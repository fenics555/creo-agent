# -*- coding: utf-8 -*-
"""plm_creo_parse.py — парсеры Creo (параметры/история/масса/размеры/фичи/семейство/
материалы/здоровье). V201: вынесены из engine.py БЕЗ изменения логики.

Чистые функции над `bytes`; зависят только от `re`/`struct`/`datetime`.
"""
import datetime
import re
import struct




# --- V125: ПАРАМЕТРЫ «КАК В CREO» (имя + тип + значение) и ТАБЛИЦА СЕМЕЙСТВА ---------------
# Владелец: «хранить параметры нужно В ТОЧНОСТИ КАК В CREO»; «все же что за ПЛМ, которая
# хранит не все параметры?»; «исполнения вообще могут иметь свои параметры, управляемые
# через уравнения или таблицу семейства»; «хранить как все параметры детали, так и все
# параметры исполнения, тогда связи будут реальные и выводиться будут без плясок».
#
# РАЗВЕДАНО НА ЖИВЫХ ФАЙЛАХ (DIN912 5.4 МБ, O-RING 6.8 МБ, G11738, DIN931, DIN7991):
#   1) ПАРАМЕТР В ФАЙЛЕ = `<ИМЯ>\x00` + тег значения (`\x27\x88\x20\xe3\x33` или `\xe2\x33`)
#      + `<ЗНАЧЕНИЕ-UTF8>\x00`.  Проверено: `NAME_1\x00'\x88 \xe33Винт   \x00`.
#   2) ТИП — в блоке `attributes`: `name.<ИМЯ>.` → `type.<N>` → `value(<тип>_val).<знач>`.
#      Типы Creo: `s_val` строка · `d_val` число · `i_val` целое · `l_val` длинное.
#   3) ТАБЛИЦА СЕМЕЙСТВА — блок `user_instances` → `user_visible_name` → `drv_tbl_ptr`
#      (генерик) + имена исполнений `<модель>[-_]<размер>`: `DIN912-M2_5X4` … (1375 вхождений
#      в DIN912; 691 в DIN931; 574 в DIN7991; 2085 в O-RING). У 618 библиотечных генериков —
#      ВСЕГО ~10 523 исполнения, и ПЛМ их НЕ читал вовсе (отсюда «мало связей по DIN912»).
#      В скилле дома это УЖЕ было (§8.3/§8.7 SKILL_creo_file_reading.md) — в код не попало.
CREO_VAL_TAG = (b"\x27\x88\x20\xe3\x33", b"\xe2\x33")

CREO_TYPES = {b"s_val": "str", b"d_val": "num", b"i_val": "int", b"l_val": "int",
              b"b_val": "bool", b"r_val": "ref"}



# 🔴 29.10.2026 — ЭВРИСТИКА РАЗБОРА ИМЕНИ СНЯТА (ЗАКОН АВТОРА, см. §104 скилла).
# Ранее здесь жил `instance_nominals()` (разбор `M3X12_G22033` → диаметр 3 / длина 12).
# ОТМЕНЕНО: имя исполнения задаёт ЧЕЛОВЕК, оно может быть любым (`401-10534_спец_исполнение`),
# поэтому любые числа из имени — ДОГАДКА. В системе учёта полуправды быть не может.
# Номиналы: только из Creo (J-Link, `tree_probe.bat`) — там они ВЫЧИСЛЕНЫ ядром.
# Цифровой базис в базе — Creo-именования: `dN` (размеры), `TYPE_*` (виды), `PROP_*` (свойства).


def _creo_clean(s):
    """Убрать служебные байты Creo по краям значения (\\x00-\\x1f) — иначе в базе мусор.

    V125: Creo ставит ПЕРЕД значением пару служебных байтов (`\\xf7\\x1d`, `\\xf7\\x1c`) —
    если их не срезать, в параметр попадает `'\\x1fDIN912-M'` вместо `'DIN912-M'`.
    """
    s = s.strip("\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f\x10\x11\x12\x13"
                "\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f \t\r\n")
    return s.lstrip("\xf7\x1c\xf7\x1d\xf7\x1e\xf7\x1f").strip()



# имя параметра: латиница/кириллица/подчёркивание, 2..31 знак (UTF-8 кириллица = 2 байта)
_RX_PNAME = rb"([A-Za-z\xd0\x90-\xd1\x8f_][A-Za-z0-9\xd0\x90-\xd1\x8f_\.]{1,30})"

# параметр: <ИМЯ>\0 <тег> <значение>\0
# V125: Creo ставит ПЕРЕД значением служебные байты `\xf7\x1c/\xf7\x1d/\xf7\x1f` —
# их надо срезать ДО декодирования, иначе `\xf7` (невалидный UTF-8) «съедает» `\x1f`
# и в значение попадает мусор (`'\x1fDIN912-M'` вместо `'DIN912-M'`).
_RX_PARAM = re.compile(_RX_PNAME + rb"\x00(?:" + b"|".join(CREO_VAL_TAG) + rb")"
                       rb"(?:\xf7[\x1c-\x1f])?(.{0,120}?)\x00", re.S)

# блок attributes: name.<ИМЯ>. ... type.<N> ... value(<тип>).<знач>
_RX_ATTR = re.compile(rb"name\." + _RX_PNAME + rb"\x00.{0,150}?value\((s_val|d_val|i_val|l_val)\)"
                      rb"\x00(.{0,120}?)\x00", re.S)



def creo_params(raw):
    """ВСЕ параметры модели «как в Creo»: [(имя, тип, значение)] — тип из блока `attributes`.

    Тип берётся по разметке Creo (`value(s_val)` = строка, `value(d_val)` = число и т. д.);
    если разметки нет (сжатый вид) — тип «str». Одно имя = одна запись (первое непустое).
    """
    out = {}
    for m in _RX_ATTR.finditer(raw):
        nm = m.group(1).decode("utf-8", "replace").strip()
        typ = CREO_TYPES.get(m.group(2), "str")
        val = _creo_clean(m.group(3).decode("utf-8", "replace"))
        if nm and val and nm not in out:
            out[nm] = (typ, val)
    for m in _RX_PARAM.finditer(raw):
        nm = m.group(1).decode("utf-8", "replace").strip()
        val = _creo_clean(m.group(2).decode("utf-8", "replace"))
        if nm and val and "\x00" not in val and nm not in out:
            out[nm] = ("str", val)
    return [(nm, t, v) for nm, (t, v) in out.items()]



# таблица семейства: имена исполнений выглядят как <генерик>[-_]<размер>
# 🔴 28.10.2026: к трём прежним маркерам добавлены `FamilyInf` / `Sld_FamilyInfo` —
# на файлах старого поколения (`g22033.prt.1`, 2019) `instances_data` НЕ пишется вовсе,
# а таблица лежит внутри `FamilyInf` (573 590 Б). Раньше такой файл отбрасывался на входе.
_RX_INST = re.compile(rb"user_instances|user_visible_name|drv_tbl_ptr|FamilyInf|Sld_FamilyInfo")



def family_of(raw, model="", path=""):
    """ТАБЛИЦА СЕМЕЙСТВА из файла ГЕНЕРИКА: [(исполнение, родитель)] — с МНОГОУРОВНЕВОСТЬЮ.

    Читается по блоку `instances_data` / `user_instances` (проверено на DIN912, DIN931, DIN7991,
    O-RING). Имена исполнений — `<модель>[-_]<типразмер>`; у каждого есть свой **родитель**
    (`drv_tbl_ptr`), поэтому таблица бывает **многоуровневой**: `DIN912-M2_5X4` → `DIN912-M2_5`
    → `DIN912`. Пустой список = модель НЕ генерик (обычная деталь).

    🔴 ГРАБЛЯ 28.10.2026 (стоп-лист эстафеты п.2): исполнения пишутся СБОРКАМ (15 937) и
    ЧЕРТЕЖАМ (11 490). Исполнение — это ВИРТУАЛЬНЫЙ вариант ВНУТРИ файла генерика; таблица
    семейства живёт во `.prt` (скилл `SKILL_creo_read_family.md` §5: настоящие модели семейств —
    590 `.prt.1` / 31 `.asm.1` / 4 `.drw.1`, но исполнения библиотечного крепежа — детали).
    Причина ошибки — та же, что в грабле 3: имя модели-генерика ВСТРЕЧАЕТСЯ в байтах блока
    `instances_data` чужого файла, и `re.finditer` по всему `raw` ловил совпадение. Проверка типа
    файла закрывает канал: НЕ деталь (`.prt`) → таблицы семейства не пишем.
    `path` пуст (старые вызовы/пробники) → проверку не применяем, поведение прежнее.

    Возвращает [(instance, parent)]: parent = '' для верхнего уровня.
    """
    # 🔴 28.10.2026 (слово владельца + замер турновера): таблица семейства БЫВАЕТ У СБОРКИ —
    # «есть сборки, у которых через таблицу семейства + сборку взаимозамены меняются компоненты
    # в исполнениях». Замер `птр-401-мт-01r-00-t01.asm.1`: instances_data 3, user_visible_name 3,
    # dim_tab_file 3, values_xar 3, param_val 3, исполнение `R-00-T01_ISP-AL` — а прежняя проверка
    # `not is_part_file` отдавала НОЛЬ. Теперь разрешены ДЕТАЛЬ и СБОРКА; чертёж (`.drw`) — нет
    # (у чертежа таблицы семейства не бывает; там же ловилась чужая запись — грабля V135).
    if not path or not model or not _RX_INST.search(raw):
        return []
    _p = path.lower()
    if not (".prt." in _p or _p.endswith(".prt") or ".asm." in _p or _p.endswith(".asm")):
        return []
    # 1) собираем пары «имя → родитель» из блока instances_data.
    # ЗАМЕР (DIN912): запись выглядит так —
    #   user_visible_name\x00…<ИМЯ>\x00\xe1\xe1\xe1\xe1\xe1…<РОДИТЕЛЬ>\x00
    # имена идут парами: `DIN912-M2_5` → `DIN912-M`, `DIN912-M2_5X4` → `DIN912-M2_5`
    # (то есть таблица МНОГОУРОВНЕВАЯ). Имя и родитель разделены `\xe1\xe1\xe1\xe1\xe1`.
    # 🔴 28.10.2026 (ЗАКОН ВЛАДЕЛЬЦА + замер байт на ДВУХ поколениях):
    #   «имя инстанса — ЛЮБОЕ, его назначает человек; то спереди, то сзади — это я так захотел».
    #   Значит разбирать имя по частям (`<модель>[-_]…`) ЗАПРЕЩЕНО — так терялись
    #   `M10_G22033` (модель в КОНЦЕ) на `g22033.prt.1` (2019) при том, что таблица занимает
    #   573 590 Б. Признак — ТОЛЬКО структура записи, одинаковая в обоих поколениях:
    #       <префикс> \xe3\x02 <ИМЯ ИСПОЛНЕНИЯ> \x00 \xe1\xe1\xe1\xe1\xe1
    #                 \xf7\x0f\x00 \xe3\x1f\xe3\x02 <ИМЯ РОДИТЕЛЯ> \x00 \xe1\xe1\xe1\xe1\xe1 \xf7\x0c\x02
    #   Замер: din912 `\xf7\x0e\xfb\xe3\xf7\x0f\xe3\x02DIN912-M2_5X4\x00…` (префикс с \xfb),
    #          g22033 `\xf4\x04\xf7\r\xe3\xe3\x02M10_G22033\x00…` (без \xfb) — маркеры \xe3\x02,
    #          разделитель \xe1×5, маркер родителя, конец записи — ОДНИ И ТЕ ЖЕ.
    pairs = {}
    # блок таблицы: от instances_data, а если его нет (старое поколение) — от FamilyInf
    blk = raw
    i = raw.find(b"instances_data")
    if i < 0:
        i = raw.find(b"FamilyInf")
    if i < 0:
        i = raw.find(b"Sld_FamilyInfo")
    if i >= 0:
        blk = raw[i:i + 400000]          # блок таблицы (дальше уже геометрия)
    for m in re.finditer(rb"\xe3\x02([\x20-\x7e\xc0-\xff]{2,64}?)\x00"       # ИМЯ исполнения
                         rb"\xe1\xe1\xe1\xe1\xe1"                            # разделитель
                         rb".{0,24}?\xe3\x1f\xe3\x02([\x20-\x7e\xc0-\xff]{2,64}?)\x00",  # РОДИТЕЛЬ
                         blk, re.S):
        nm = _creo_clean(m.group(1).decode("utf-8", "replace"))
        par = _creo_clean(m.group(2).decode("utf-8", "replace"))
        if nm and len(nm) >= 2 and nm != model:
            pairs.setdefault(nm, par or model)
    # 2) имена, найденные структурой, — этого достаточно. Если структура не дала ничего,
    #    ВТОРОЙ канал: все имена вида `<имя файла>-<суффикс>` (старые файлы, где таблица
    #    писалась иначе). ЗАПАСНОЙ, не основной: вид имени — не признак (закон владельца).
    seen, out = set(), []
    for nm, par in pairs.items():
        seen.add(nm)
        out.append((nm, par))
    if not out:
        base = re.escape(model.encode("utf-8", "replace"))
        for m in re.finditer(base + rb"[-_][A-Za-z0-9_\-\.]{1,30}", raw):
            s = _creo_clean(m.group(0).decode("utf-8", "replace"))
            if s and s != model and s not in seen:
                seen.add(s)
                out.append((s, model))
    return out



# --- V126: ИСТОРИЯ ПРАВОК «КТО И КОГДА» — КОМПЬЮТЕР + ПОЛЬЗОВАТЕЛЬ + ВРЕМЯ --------------------
# Владелец: «+ что когда правилось и кем (имя компьютера + юзер)».
#
# РАЗВЕДАНО НА ЖИВЫХ ФАЙЛАХ (G11738.prt.1): Creo пишет в файл КАЖДУЮ запись истории:
#   полный вид:  user_name\x00\xf1USER\x00\xe0\x00modif_time\x00\xe2
#                tm_sec\x00<1б> tm_min\x00<1б> tm_hour\x00<1б> tm_mday\x00<1б> tm_mon\x00<1б> tm_year\x00<1б>
#                typed_data(<ВИД>)\x00\xf1\xe3 rev_string\x00<НОМЕР>\x00
#                comment\x00<UTF-8>"Наименование компьютера: '<КОМПЬЮТЕР>'"\x00 Proe_version\x00<"Creo X.Y.Z">
#   сжатый вид:  \xf7\x14USER\x00\xe2 <sec><min><hour><mday><mon><year>   (6 байт времени)
# ВАЖНО: поле `user_name` почти всегда = служебное «USER»; РЕАЛЬНЫЙ КОМПЬЮТЕР/ПОЛЬЗОВАТЕЛЬ
# лежит в `comment`: «Наименование компьютера: 'Konstruktor-2'» (бывает 'frezer-4', 'Valeriy').
# Год = 1900 + байт, месяц = байт + 1 (проверено: 2026-10-02 11:42:07).
_CREO_PC_MARK = "Наименование компьютера: '".encode("utf-8")

_RX_HIST_SHORT = re.compile(rb"\xf7\x14([\x20-\x7e]{1,24}?)\x00\xe2"
                            rb"(.)(.)(.)(.)(.)(.)")



def creo_history(raw):
    """ИСТОРИЯ ПРАВОК из файла Creo: [{user, computer, creo, ts, rev, action}] — КАК В CREO.

    Владелец: «что когда правилось и кем (имя компьютера + юзер)». Берём ВСЕ записи журнала.
    ЗАМЕР на G11738: коротких времён (каждая операция) — 4833, а «компьютер» (`comment`) — лишь 9
    (Creo пишет компьютер ТОЛЬКО при сохранении модели, `typed_data(MdlStored)`). Поэтому
    компьютер привязываем к БЛИЖАЙШЕМУ времени ПЕРЕД ним по позиции в файле, а не по индексу.
    """
    events = []          # (позиция, вид, данные)
    # V126: между полями времени стоит разделитель `\xe0\x01` (проверено на живом файле:
    # `tm_sec\x00\x07\xe0\x01tm_min\x00\x2a…`) — БЕЗ него шаблон не находил НИ ОДНОГО времени,
    # и все «компьютеры» прилипали к единственной пустой записи.
    for m in re.finditer(rb"tm_sec\x00(.)\xe0\x01tm_min\x00(.)\xe0\x01tm_hour\x00(.)"
                         rb"\xe0\x01tm_mday\x00(.)\xe0\x01tm_mon\x00(.)\xe0\x01tm_year\x00(.)",
                         raw, re.S):
        sec, mi, h, d, mo, y = (b[0] for b in m.groups())
        events.append((m.start(), "t", (sec, mi, h, d, mo, y)))
    for m in _RX_HIST_SHORT.finditer(raw):
        sec, mi, h, d, mo, y = (b[0] for b in m.groups()[1:7])
        events.append((m.start(), "t", (sec, mi, h, d, mo, y)))
    # V126: компьютер + версия Creo. Формат записи (проверено):
    #   \xf7\x14USER\x00\xe2<6 байт времени>\xe3<rev>\x00 … \x00<"Наименование компьютера: 'X'">\x00Creo <ver>
    # поэтому компьютер относим к ПОСЛЕДНЕЙ записи времени ПЕРЕД ним (а не по индексу).
    for m in re.finditer(re.escape(_CREO_PC_MARK) + rb"([^']{0,60})'\x00([^\x00]{0,24})", raw, re.S):
        events.append((m.start(), "pc", (m.group(1).decode("utf-8", "replace").strip(),
                                         m.group(2).decode("utf-8", "replace").strip())))
    for m in re.finditer(rb"rev_string\x00(.{0,12}?)\x00", raw):
        events.append((m.start(), "rev", m.group(1).decode("utf-8", "replace").strip()))
    events.sort(key=lambda x: x[0])

    out, last_ts = [], ""
    for _pos, kind, data in events:
        if kind == "t":
            sec, mi, h, d, mo, y = data
            try:
                dt = datetime.datetime(1900 + y, mo + 1, d, h, mi, sec)
            except ValueError:
                continue
            if not (1990 <= dt.year <= 2040):
                continue
            last_ts = dt.strftime("%d.%m.%Y %H:%M:%S")
            out.append({"user": "USER", "computer": "", "creo": "", "ts": last_ts,
                        "rev": "", "action": ""})
        elif kind == "pc":
            comp, creo = data
            # компьютер относится к ПОСЛЕДНЕЙ записи времени (сохранение модели)
            if out:
                out[-1]["computer"] = comp
                out[-1]["creo"] = creo
            else:
                out.append({"user": "USER", "computer": comp, "creo": creo,
                            "ts": last_ts, "rev": "", "action": ""})
        elif kind == "rev":
            if out:
                out[-1]["rev"] = data
    return out



# --- V127: ЗДОРОВЬЕ ФАЙЛА CREO (регенерация, статус модели, «не использовать») ---------------
# Владелец: «Нужно знать историю и ЗДОРОВЬЕ файлов крео». Разведано в файлах (DIN912, G11738,
# DIN931, O-RING): `reg_status` (флаг регенерации: `\x00` = ок, иное = требует регенерации),
# `MdlStatus`/`Sld_MdlStatus` (статус модели), `mdl_geom_rev` (ревизия геометрии),
# `inactive_geom` («не использовать» — неактивная геометрия).
_RX_REG = re.compile(rb"reg_status\x00(.)", re.S)

_RX_E32 = re.compile(rb"\xe3\x32")



def _e32_decode(body7):
    """7 байт после `e3 32 [тип]` → список кандидатов (lead, значение). §167."""
    out = []
    for lead in (0x40, 0x41, 0x3F, 0x42, 0x3E, 0x43):
        try:
            v = struct.unpack(">d", bytes([lead]) + body7)[0]
        except struct.error:
            continue
        if 1e-9 < abs(v) < 1e12:
            out.append((lead, v))
    return out



def creo_mass_props(raw):
    """{имя: значение} — масса/объём/плотность (валидация плотностью металла). §167/§174."""
    out, vals = {}, []
    for m in _RX_E32.finditer(raw):
        s = m.end()
        if s + 8 > len(raw):
            continue
        for lead, v in _e32_decode(raw[s + 1:s + 8]):
            vals.append(v)
    if not vals:
        return out
    masses = [v for v in vals if 1e-6 <= v <= 1e4]
    vols = [v for v in vals if 1.0 <= v <= 1e8]
    best = None
    for mg in masses:
        for vg in vols:
            rho = mg / vg * 1e6
            if 6.0 <= rho <= 9.5 and (best is None or abs(rho - 7.85) < best[0]):
                best = (abs(rho - 7.85), mg, vg, rho)
    if best:
        out["PRO_MP_MASS"], out["PRO_MP_VOLUME"], out["PRO_MP_DENSITY"] = best[1], best[2], best[3]
    return out



_RX_DIM_ENTRY = re.compile(rb"dim_type\x00(.)\xe0\x01feat_id\x00(.)", re.S)



def creo_dimensions(raw):
    """[{feat_id,dim_type,nominal,tol_class,tol_type,bound}] — номинал `2F B1 B2`. §173."""
    out = []
    for m in _RX_DIM_ENTRY.finditer(raw):
        seg = raw[m.end():m.end() + 400]
        nom = None
        for mm in re.finditer(rb"\x2f(.)(.)", seg):
            b1, b2 = mm.group(1)[0], mm.group(2)[0]
            lead = 0x40 if b1 >= 0x40 else 0x3F
            try:
                v = struct.unpack(">d", bytes([lead, b1, b2, 0, 0, 0, 0, 0]))[0]
            except struct.error:
                continue
            if 0.01 <= v <= 1e6:
                nom = round(v, 6)
                break
        mc = re.search(rb"tol_class\x00(.)", seg)
        mt = re.search(rb"tol_type\x00(.)", seg)
        mb = re.search(rb"bound\x00(.)", seg)
        out.append({"feat_id": m.group(2)[0], "dim_type": m.group(1)[0], "nominal": nom,
                    "tol_class": mc.group(1)[0] if mc else None,
                    "tol_type": mt.group(1)[0] if mt else None,
                    "bound": mb.group(1)[0] if mb else None})
    return out



def creo_features(raw, feat_dict=None):
    """[{defs,typenum,typename,feat_id,symbol_key,seq}] — `feat_defs_<N> − 910`. §171."""
    D = feat_dict if feat_dict is not None else _feattype_dict()
    out = []
    for seq, m in enumerate(re.finditer(rb"feat_defs_(\d+)", raw)):
        n = int(m.group(1))
        seg = raw[m.end():m.end() + 140]
        mi = re.search(rb"id\x00(.)", seg)
        ms = re.search(rb"symbol_key\x00(.)", seg)
        out.append({"defs": n, "typenum": n - 910, "typename": D.get(n - 910, "?"),
                    "feat_id": mi.group(1)[0] if mi else None,
                    "symbol_key": ms.group(1)[0] if ms else None, "seq": seq})
    return out



_FEATTYPE_CACHE = None



def _feattype_dict():
    """Словарь `pfcFEATTYPE` (314) из заголовков Creo. §171. Кэшируется."""
    global _FEATTYPE_CACHE
    if _FEATTYPE_CACHE is not None:
        return _FEATTYPE_CACHE
    _FEATTYPE_CACHE = {}
    for _p in (r"D:\PTC\CREO13\Creo 13.4.1.0\Common Files\otk\otk_cpp\include\pfcFeature.h",
               r"D:\PTC\CREO12\Creo 12.4.2.0\Common Files\otk\otk_cpp\include\pfcFeature.h"):
        try:
            _t = open(_p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        _m = re.search(r"enum pfcFeatureType\s*\{(.*?)\}", _t, re.S)
        if _m:
            _items = [x.strip() for x in _m.group(1).split(",") if x.strip()]
            _FEATTYPE_CACHE = {i: n.replace("pfcFEATTYPE_", "") for i, n in enumerate(_items)}
            break
    return _FEATTYPE_CACHE



def creo_equations(raw):
    """[{kind,name,old_val,new_val,feat_id}] — ДВА МЕСТА (§174): Relations + пострегенерация."""
    out = []
    for m in re.finditer(rb"chg_param_arr", raw):
        seg = raw[m.end():m.end() + 3000]
        for nm in re.finditer(rb"(PRO_MP_[A-Z_0-9]+)\x00", seg):
            tail = seg[nm.end():nm.end() + 600]
            mf = re.search(rb"feat_id\x00(.)", seg[:nm.start()] or seg)
            out.append({"kind": "postregen", "name": nm.group(1).decode(),
                        "old_val": "old_state(p_val)" if b"old_state" in tail else "",
                        "new_val": "new_state(p_val)" if b"new_state" in tail else "",
                        "feat_id": mf.group(1)[0] if mf else None})
            break
    for _ in re.finditer(rb"param_restr_entry", raw):
        out.append({"kind": "relation", "name": "param_restr_entry",
                    "old_val": "", "new_val": "", "feat_id": None})
    return out



def creo_materials(raw):
    """{name, description, mtype} — материал модели."""
    out = {}
    for key, pat in (("name", rb"PTC_MASTER_MATERIAL\x00([\x20-\x7e\xc0-\xff]{1,60})\x00"),
                     ("description", rb"PTC_MATERIAL_DESCRIPTION\x00([\x20-\x7e\xc0-\xff]{1,80})\x00"),
                     ("mtype", rb"PTC_MATERIAL_TYPE\x00([\x20-\x7e]{1,40})\x00")):
        m = re.search(pat, raw)
        if m:
            out[key] = m.group(1).decode("utf-8", "replace")
    return out



def creo_health(raw):
    """ЗДОРОВЬЕ файла Creo: {regen, reg_status, inactive, geom_rev} — без запуска Creo.

    Владелец: «Нужно знать историю и здоровье файлов крео». Читаем признаки, которые Creo
    пишет в файл: `reg_status` (0 = модель регенерирована, иное = требует регенерации),
    наличие неактивной геометрии (`inactive_geom`), ревизию геометрии (`mdl_geom_rev`).
    """
    out = {"regen": "", "reg_status": "", "inactive": 0, "geom_rev": ""}
    m = _RX_REG.search(raw)
    if m:
        b = m.group(1)[0]
        out["reg_status"] = str(b)
        out["regen"] = "ok" if b == 0 else "требует регенерации"
    elif b"MdlStatus" in raw or b"Sld_MdlStatus" in raw:
        out["regen"] = "статус есть"
    out["inactive"] = len(re.findall(rb"inactive_geom", raw))
    m2 = re.search(rb"mdl_geom_rev\x00(.{0,12}?)\x00", raw, re.S)
    if m2:
        _g = _creo_clean(m2.group(1).decode("utf-8", "replace"))
        # V127: значение бывает «ссылочным» (нечитаемые байты) — берём только печатаемое
        if _g and all(ch.isprintable() for ch in _g):
            out["geom_rev"] = _g
    return out

extract_family_info = family_of

