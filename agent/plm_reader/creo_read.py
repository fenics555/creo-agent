# -*- coding: utf-8 -*-
r"""creo_read — ЕДИНЫЙ ЧИТАТЕЛЬ ФАЙЛОВ CREO «В ЛОБ» (общая библиотека дома).

Одна реализация чтения — её используют инструменты (`plm_tree`, `plm_reader`), чтобы не плодить
копии парсера. Creo не нужен, только стандартная библиотека.
"""
import datetime
import os
import re
import struct
from collections import Counter

TAIL = re.compile(rb"\xf7(.)\xe3([0-9]{1,7})\x00\x00(.{0,220}?)\x00((?:Creo )?[0-9][0-9.]*)\x00", re.S)
STAMP = re.compile(rb"\xf7\x14([\x20-\x7e\xc0-\xff]{1,24}?)\x00\xe2(.)(.)(.)(.)(.)(.)", re.S)
STAMP2 = re.compile(rb"\xe1\xf6\xe1([\x20-\x7e\xc0-\xff]{1,24}?)\x00\xe2(.)(.)(.)(.)(.)(.)", re.S)
NAME_B = re.compile(rb"[\x00-\x1f\x80-\xff]([A-Za-z0-9][A-Za-z0-9_\-\.]{3,47}\.(?:PRT|ASM))",
                    re.IGNORECASE)


def stem(name):
    """Имя файла → код модели (верхний регистр, без версии и расширения)."""
    n = name.upper()
    for ext in (".PRT", ".ASM", ".DRW", ".NEU", ".SEC", ".M_P", ".PRT.", ".ASM."):
        if ext in n:
            n = n.split(ext)[0]
            break
    return re.sub(r"\.\d+$", "", n)


def read(path):
    with open(path, "rb") as f:
        return f.read()


def parse_toc(raw):
    """Оглавление секций файла: {имя: (offset, length)} по цепочке NEXT_TOC_ENTRY."""
    out, pos = {}, raw.find(b"#UGC_TOC")
    for _ in range(20):
        if pos < 0:
            break
        p = raw.find(b"\n", pos)
        nxt = -1
        while True:
            e = raw.find(b"\n", p + 1)
            if e < 0:
                break
            line = raw[p + 1:e].decode("ascii", "replace").strip()
            p = e
            if line.startswith("NEXT_TOC_ENTRY"):
                nxt = int(line.split()[1], 16)
                break
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_:]{1,40}) ([0-9a-f]{2,8}) ([0-9a-f]{2,8})"
                         r"(?: ([0-9a-f]{2,8}))?(.*)$", line)
            if m and (not m.group(5).strip() or m.group(5).strip()[0] in "0123456789-"):
                ln = int(m.group(4), 16) if m.group(4) else int(m.group(3), 16)
                key = m.group(1)
                # Normalize ND: keys
                nd_re = re.compile(r"^ND:\d+:(.+?)(?::\d+)?$")
                nd_match = nd_re.match(key)
                if nd_match:
                    key = nd_match.group(1)
                out[key] = (int(m.group(2), 16), max(ln, 1))
        if nxt < 0 or nxt >= len(raw):
            break
        pos = nxt
    return out


def _endian(raw):
    return "big" if b"MACH SUN_SunOS" in raw[:512] else "little"

# Правдоподобные пределы (V106): Creo-модель не бывает 1000 м³ и не бывает отрицательной.
# Грабля владельца: в таблице появлялся «объём» из ~400 цифр (1.37e+290) — это БИТЫЙ double
# (случайные 8 байт попали на шаблон `e0 02 volume 00 ed`). Такой мусор ломал и фильтр
# (`CAST(volume AS TEXT) LIKE '%170%'` ловил цифры), и сортировку.
VOL_MIN, VOL_MAX = 0.0, 1e9          # мм³: от 0 до 1000 м³


def _sane_number(v):
    """Отсеять мусорный double: NaN/inf/отрицательный/сверхбольшой → None."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f or f in (float("inf"), float("-inf")):      # NaN / inf
        return None
    if f < VOL_MIN or f > VOL_MAX:
        return None
    return f


def real(raw, key):
    """Числовое поле `e0 02 <имя> 00 ed <8 байт BE double>` (объём, масса).

    V106: значение проверяется `_sane_number` — битые double (1e+290 и т.п.) отбрасываются,
    чтобы в базе и в таблице не появлялись «объёмы» из сотен цифр.
    """
    m = re.search(rb"\xe0\x02" + key.encode() + rb"\x00\xed", raw)
    if not m or m.end() + 8 > len(raw):
        return None
    fmt = ">d" if _endian(raw) == "big" else "<d"
    try:
        return _sane_number(struct.unpack(fmt, raw[m.end():m.end() + 8])[0])
    except Exception:
        return None


def params(raw, toc):
    """Параметры изделия `<имя>\\0 e2 33 <текст>`: сначала секция NeuPrtSld, затем — по ВСЕМУ файлу
    (у .asm/.prt часть параметров лежит вне этой секции: МАТЕРИАЛ, PTC_MATERIAL_NAME, НАИМЕНОВАНИЕ…)."""
    out = {}
    off, ln = toc.get("NeuPrtSld", (0, 0))
    for src in (raw[off:off + ln], raw):
        for m in re.finditer(
                rb"([\x20-\xff]{3,32})\x00(?:\xe2\x33|\x27\x88\x20\xe3\x33)(.{0,80}?)\x00", src, re.S):
            try:
                t = m.group(1).decode("utf-8", "replace").strip()
            except Exception:
                t = m.group(1).decode("cp1251", "replace").strip()
            
            try:
                v = m.group(2).decode("utf-8", "replace").strip()
            except Exception:
                try:
                    v = m.group(2).decode("cp1251", "replace").strip()
                except Exception:
                    continue
                    
            if t and v and "\x00" not in v:
                out[t] = v
    return out


VAL_TAGS = (b"\xe2\x33", b"\x27\x88\x20\xe3\x33")   # значение параметра | значение отношения


def param(raw, names, default=""):
    """Значение параметра по списку имён — ищем по ВСЕМУ файлу, в UTF-8 и cp1251, по всем тегам значения.
    Параметр может быть задан и вручную, и уравнением — берём первое найденное НЕПУСТОЕ значение."""
    for nm in names:
        if not nm:
            continue
        for enc in ("utf-8", "cp1251"):
            try:
                nb = nm.encode(enc)
            except Exception:
                continue
            pos = 0
            while True:
                i = raw.find(nb, pos)
                if i < 0:
                    break
                pos = i + 1
                if i > 0:                        # не хвост длинного имени (…_NAME, PTC_MATERIAL_NAME)
                    pb = raw[i - 1]
                    if pb == 0x5F or 0x30 <= pb <= 0x39 or 0x41 <= pb <= 0x5A or 0x61 <= pb <= 0x7A:
                        continue
                h = raw[i + len(nb): i + len(nb) + 12]
                for tag in VAL_TAGS:
                    if h.startswith(b"\x00" + tag):
                        v = raw[i + len(nb) + 1 + len(tag):]
                        if v[:1] == b"\xf7":     # служебный префикс записи: f7 + байт-флаг
                            v = v[2:]
                        j = v.find(b"\x00")
                        if j < 0:
                            j = 48
                        v = v[:j]
                        try:
                            s = v.decode("utf-8")
                        except UnicodeDecodeError:
                            try:
                                s = v.decode("cp1251")
                            except Exception:
                                continue
                        s = " ".join(s.split())
                        if s and "\x00" not in s:
                            return s
    return default


def compose(raw, rule):
    """Собрать значение по ПРАВИЛУ-шаблону:
      `{ИМЯ}`  — значение параметра;  `"текст"` — литерал (КАВЫЧКИ НЕ ВЫВОДЯТСЯ);
      `+` и пробелы между частями — только склейка (в значение не попадают).
    Пустые параметры отбрасываются, лишние пробелы сжимаются.
    Правило без `{` и `"` — просто имя параметра.
    """
    rule = rule or ""
    if "{" not in rule and '"' not in rule:
        return param(raw, [rule.strip()])
    out, i, n = [], 0, len(rule)
    while i < n:
        c = rule[i]
        if c == "{":
            j = rule.find("}", i)
            if j < 0:
                break
            v = param(raw, [rule[i + 1:j].strip()])
            if v:
                out.append(v)
            i = j + 1
        elif c == '"':
            j = rule.find('"', i + 1)
            if j < 0:
                break
            out.append(rule[i + 1:j])
            i = j + 1
        elif c == "+":
            i += 1
        elif c.isspace():
            out.append(" ")                    # пробел в правиле = пробел в выводе
            i += 1
        else:
            j = i
            while j < n and rule[j] not in '{+"':
                j += 1
            out.append(rule[i:j])
            i = j
    return " ".join("".join(out).split())


def role(raw, stems=frozenset(), me=""):
    """Роль изделия по правилам §8.5 (имя файла НЕ признак):
    `MFG` — сборка `ASSEM_MFG`; `nasled.<родитель>` — `MERGE_BASE_PART` (отражение/базовая деталь);
    `nasled.<СВОЙСТВО>` — наследование СВОЙСТВА (`PTC_*`/`layers`/`restrict_table` — скилл §7);
    `proizv.<родитель>` — `ref_part_tab.name` из ТОЙ ЖЕ папки (у обычной детали там шаблонный
    `MM_ASSY`/`SBORKA_MM` — не роль, поэтому сверяем с именами папки).

    🔴 V139 (28.10.2026): ПЕРЕПИСАНО. Старый код брал родителя РЕГУЛЯРКОЙ `.{0,80}?` + `latin-1` —
    скилл §5 п.1 это ЗАПРЕЩАЕТ: кириллица превращалась в мусор, а имя обрезалось. Теперь разбор
    идёт ТЕМ ЖЕ кодом, что и сканер (`engine.merge_base_parts` / `ref_part_parents`) — одна правда.

    🔴 28.10.2026 (владелец: «нужно уметь читать ВСЕ файлы Creo»): `me` — это ИМЯ ФАЙЛА в вызове
    (`role(raw, fstems, s)`), поэтому по нему же определяем КОПИИ и ВСПОМОГАТЕЛЬНЫЕ форматы
    (`.xpr`, `.crc`, `.mfg`, `.m_p`, `.frm`, `.lay`, `.sec`, `.neu`). Замер: `paralelka_15x4.xpr`
    (209 918 Б) — полноценная модель-копия, но ни `MERGE_BASE_PART`, ни `ref_part_tab` там нет,
    и роль возвращалась пустой → в дереве файл не отличим от мусора.
    """
    try:
        import engine as _e0
        _ext_role = _e0.role_by_path(me or "")
        if _ext_role:
            return _ext_role
    except Exception:
        pass
    if b"ASSEM_MFG" in raw[:400]:
        return "MFG"
    try:
        import engine as _eng                      # локальный импорт: разрыв цикла creo_read <-> engine
        mb = _eng.merge_base_parts(raw)
    except Exception:
        mb = []
    if not mb:                                     # запасной путь, если движка рядом нет
        if b"MERGE_BASE_PART" in raw:
            i = raw.find(b"\xe3\x33\xf7\x1c")
            if i >= 0:
                nm = raw[i + 4:raw.find(b"\x00", i + 4)]
                s2 = nm.decode("utf-8", "replace").strip()
                if s2:
                    mb = [(s2, "наследование")]
    if mb:
        # 🔴 28.10.2026 (замер литейки): первый элемент бывает СВОЙСТВОМ (`PTC_MASTER_MATERIAL`,
        # `DISTORTION ENERGY (VON MISES)`, `CHUGUN_VCH50`), а не моделью. Роль строим по ПЕРВОЙ
        # МОДЕЛИ; свойства не теряются — они идут каналом `prop` (`derived_all`/`props_all`).
        base = mb[0][0]
        try:
            import engine as _eng1
            base = _eng1.first_model_name([m[0] for m in mb]) or base
        except Exception:
            pass
        if base and base.upper() not in ("MM_ASSY", "MM_PART", "SBORKA_MM", "SBORKA_MFG", "MFG_NC"):
            return "nasled." + base
    try:
        import engine as _eng2
        rp = _eng2.ref_part_parents(raw)
    except Exception:
        rp = []
    for p in rp:
        s = stem(p)
        if s != me and (not stems or s in stems):
            return "proizv." + p
    return ""


def user_time(raw):
    """Все пары (позиция, пользователь, дата) из истории — по возрастанию позиции.
    Две раскладки записи: `f7 14 <user> 00 e2 <6 байт>` и `e1 f6 e1 <user> 00 e2 <6 байт>`."""
    out = []
    for rx in (STAMP, STAMP2):
        for m in rx.finditer(raw):
            s, mi, h, d, mo, y = (b[0] for b in m.groups()[1:])
            try:
                dt = datetime.datetime(1900 + y, mo + 1, d, h, mi, s)
            except ValueError:
                continue
            if 1990 <= dt.year <= 2030:
                try:
                    who = m.group(1).decode("utf-8")
                except UnicodeDecodeError:
                    who = m.group(1).decode("cp1251", "replace")
                out.append((m.start(), who, dt))
    return sorted(set(out))


def last_hist(raw):
    """Последняя запись истории: (ревизия, пользователь, дата 'дд.мм.гг чч:мм')."""
    st, last = user_time(raw), None
    for t in TAIL.finditer(raw):
        prev = [s for s in st if s[0] < t.start()]
        last = (t.group(2).decode(), prev[-1][1] if prev else "",
                prev[-1][2].strftime("%d.%m.%y %H:%M") if prev else "")
    return last


def names(raw):
    """Имена моделей внутри файла (расширение срезано) и сколько раз встречаются (входимость)."""
    c = Counter()
    for m in NAME_B.finditer(raw):
        c[stem(m.group(1).decode("latin-1"))] += 1
    return c


# --- ПРЕВЬЮ ИЗ ФАЙЛА (перенесено из plm_graph.py, V140, 28.10.2026) ----------
# Владелец: «Скан же должен и превью собирать, если оно читается в лоб???»
# Логика вырезки живёт ЗДЕСЬ (общий модуль чтения Creo), потому что читает ФАЙЛ.
# Показ (plm_graph) обязан только брать готовое и НЕ читать файлы (правило §96.1).

_SOF = [bytes([0xFF, c]) for c in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                                   0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF)]


def jpeg_size(d):
    """(ширина, высота) JPEG по SOF. (0,0) — не валидный JPEG (мусор)."""
    i, n = 2, len(d)
    while i < n - 9:
        if d[i] != 0xFF:
            i += 1
            continue
        mk = d[i:i + 2]
        if mk in _SOF:
            return int.from_bytes(d[i + 7:i + 9], "big"), int.from_bytes(d[i + 5:i + 7], "big")
        if mk == b"\xff\xd8" or 0xD0 <= d[i + 1] <= 0xD9:
            i += 2
            continue
        ln = int.from_bytes(d[i + 2:i + 4], "big")
        if ln < 2:
            return 0, 0
        i += 2 + ln
    return 0, 0


def _find_jpg(raw):
    """Первый ВАЛИДНЫЙ JPEG (сигнатура + проверка маркера SOF). (bytes,'jpg')|(b'','')."""
    j = -1
    while True:
        j = raw.find(b"\xff\xd8\xff", j + 1)
        if j < 0:
            return b"", ""
        e = raw.find(b"\xff\xd9", j + 3)
        if e <= 0:
            continue
        cand = raw[j:e + 2]
        if len(cand) < 2048:
            continue
        w, h = jpeg_size(cand)
        if w and h and 16 <= w <= 4096 and 16 <= h <= 4096:
            return cand, "jpg"


def _find_bmp(raw):
    """Первый ВАЛИДНЫЙ BMP (размер и WxH из заголовка). (bytes,'bmp')|(b'','')."""
    b = -1
    while True:
        b = raw.find(b"BM", b + 1)
        if b < 0 or b + 26 > len(raw):
            return b"", ""
        size = int.from_bytes(raw[b + 2:b + 6], "little")
        w = int.from_bytes(raw[b + 18:b + 22], "little", signed=True)
        h = int.from_bytes(raw[b + 22:b + 26], "little", signed=True)
        if 1024 <= size <= len(raw) - b and 16 <= abs(w) <= 4096 and 16 <= abs(h) <= 4096:
            return raw[b:b + size], "bmp"


def cut_preview(raw, want="both"):
    """Превью из файла: ПО СИГНАТУРЕ (TOC-офсет DwgData НЕ ведёт к картинке!).

    want: "both" — что найдётся (важно: в файлах бывает ТОЛЬКО JPEG, даже у .drw);
          "jpg" | "bmp" — строго этот формат; "all" — вернуть список ВСЕХ найденных.
    Возвращает (bytes, 'jpg'|'bmp') или (b'', ''); для "all" — [(bytes, ext), …].
    """
    if want == "all":
        out = []
        j, e = _find_jpg(raw)
        if j:
            out.append((j, e))
        b, e = _find_bmp(raw)
        if b:
            out.append((b, e))
        return out
    j, e1 = _find_jpg(raw)
    b, e2 = _find_bmp(raw)
    if want == "jpg":
        return (j, e1)
    if want == "bmp":
        return (b, e2)
    return (j, e1) if j else (b, e2)


def passport(path, stems=()):
    """Паспорт модели из файла (Creo не нужен)."""
    raw = read(path)
    pr = params(raw, parse_toc(raw))
    vol = real(raw, "volume") or real(raw, "mtrl_volume")
    nm = names(raw)
    refs = {c: nm[c] for c in nm if c != stem(os.path.basename(path)) and c in stems and len(c) >= 5}
    h = last_hist(raw) or ("", "", "")
    return {"path": path, "size": len(raw), "mtime": os.path.getmtime(path),
            "volume": vol or 0.0, "material": pr.get("PTC_MATERIAL_NAME") or pr.get("PTC_MASTER_MATERIAL") or "",
            "name": pr.get("\u041d\u0410\u0418\u041c\u0415\u041d\u041e\u0412\u0410\u041d\u0418\u0415") or "",
            "designation": pr.get("\u041e\u0411\u041e\u0417\u041d\u0410\u0427\u0415\u041d\u0418\u0415") or "",
            "rev": h[0], "author": h[1], "revdate": h[2],
            "role": role(raw, stems, stem(os.path.basename(path))), "refs": refs}
