# -*- coding: utf-8 -*-
"""plm_links.py — ЕДИНСТВЕННЫЙ ИСТОЧНИК СВЯЗЕЙ PLM Reader (ДОГМА §4 и §5, 28.10.2026).

ЗАКОН ВЛАДЕЛЬЦА (дословно): «СВЯЗИ ТОЛЬКО ОДНИ И СТРОЯТСЯ ОНИ ТОЛЬКО ИЗ ОДНОЙ БАЗЫ!
ВЫВОДИТЬ можно по-разному, но ПРАВИЛЬНОЕ ПОСТРОЕНИЕ МОЖЕТ БЫТЬ ТОЛЬКО ОДНО!»

ПОЧЕМУ ЭТОТ ФАЙЛ: до него связи строились в **41 месте** (`engine.py` 24 · `plm_graph.py` 7 ·
`plm_toolwin.py` 5 · `plm_dbview.py` 5) — и каждое место имело СВОЙ фильтр. Из-за этого окно,
граф и HTML показывали РАЗНЫЕ связи (владелец: «везде всё разное, но такого не может быть в ПЛМ»).
Теперь построение ОДНО и живёт ЗДЕСЬ; окна лишь ПО-РАЗНОМУ ПОКАЗЫВАЮТ эти связи.

МОДЕЛЬ ДАННЫХ (4 канала — больше нет):
    db       — СОСТАВ: `links.source IN ('asm_comp','plm_tree', NULL)` (физическое вхождение)
    family   — ИСПОЛНЕНИЯ: `links.source='family'` (генерик → исполнение, ВИРТУАЛЬНОЕ)
    inherit  — НАСЛЕДОВАНИЕ: `derived` (копия / производная / зеркало)
    mentions — УПОМИНАНИЕ имени в байтах: НЕ СВЯЗЬ, в показ НЕ идёт НИГДЕ (единообразно)

ПРАВИЛО: если канал отсеян — он отсеян ВЕЗДЕ; если показан — показан ВЕЗДЕ. Разница между окнами
может быть только в ФИЛЬТРЕ ПОКАЗА (настройки), а не в наборе связей.
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))

# Служебные «модели» (шаблоны/внутренние базы Creo) — это НЕ изделия, их связь = мусор.
# Тот же смысл, что `SVC` в plm_graph. Держать согласованным с `engine.service_stems()`.
_SVC_RX = re.compile(r"^(SBORKA_MM|SBORKA_MFG|MFG_NC|MFG_NC_NEW|INLBS_MFG_NC|MM_PART|"
                     r"MM_ASSY|MM_|TEMPLATE|REGEN_BACKUP|NONE|NULL)$", re.I)

CHANNELS = ("db", "family", "inherit", "mentions")   # 4 канала, больше нет
PHYSICAL = ("db",)                                   # «физический состав»


# ═══════════════════════════════════════════════════════════════════════════════════════
# СЛОВАРЬ ВИДОВ СВЯЗЕЙ — ЕДИНЫЙ ИСТОЧНИК ПОДПИСЕЙ, ЗНАКОВ И ЦВЕТОВ (30.10.2026)
# Владелец: «связи должны быть разборчивыми: зеркальное отражение / булевые операции /
# наследование… ну может только более понятно» + «предложи ХОРОШИЕ варианты, чтобы было
# понятно, эстетично, красиво».
#
# ТРИ ОСИ (независимые): НАПРАВЛЕНИЕ · ВИД · ПРОИСХОЖДЕНИЕ.
# Вид берётся из ФАКТА базы (не выдуман): `derived.kind` (наследование/производная/копия)
# и `links.source` (asm_comp/family/plm_tree/built_*). См. замер в STATE.md (фаза 40).
# ═══════════════════════════════════════════════════════════════════════════════════════

# код вида → {подпись, знак, цвет, стиль линии, что значит}
KINDS = {
    "structure": {"label": "структура",   "sign": "⬛", "color": "#4a90d9", "dash": "solid",
                  "about": "сборка → деталь (физическое вхождение)"},
    "inherit":   {"label": "наследование", "sign": "◉", "color": "#b07cd9", "dash": "dash",
                  "about": "построена на базе / зеркало (MERGE_BASE_PART)"},
    "derive":    {"label": "производная",  "sign": "⬡", "color": "#e0a030", "dash": "dashdot",
                  "about": "заготовка / отливка (ref_part_tab)"},
    "copy":      {"label": "копия",        "sign": "⧉", "color": "#4fb884", "dash": "double",
                  "about": "пересохранена из другой модели (from_mdl_name)"},
    "variant":   {"label": "исполнение",   "sign": "⬢", "color": "#d97a9b", "dash": "dot",
                  "about": "вариант семейства (generic → instance)"},
    "mention":   {"label": "упоминание",   "sign": "⋯", "color": "#6f8499", "dash": "dotted",
                  "about": "только текст в байтах — НЕ связь (в граф не идёт)"},
}

# НАПРАВЛЕНИЕ (куда читать связь) → подпись и стрелка
DIRS = {
    "down": {"label": "состав",     "arrow": "⬇", "about": "из чего состоит"},
    "up":   {"label": "входит в",   "arrow": "⬆", "about": "куда входит (достроено)"},
    "base": {"label": "основа",     "arrow": "↺", "about": "на чём построена"},
}


def kind_code(source, channel):
    """ЕДИНЫЙ код вида связи — из `source` (базы) и канала. ОДНО правило на весь инструмент.

    Коды Creo не выносим в показ: `asm_comp`/`plm_tree` → `structure`, `family` → `variant`,
    `built_in` → `structure` (достроено), `обратное наследование` → `inherit` и т.д.
    """
    s = (source or "").strip().lower()
    if channel == "mention" or s == "mentions":
        return "mention"
    if channel == "variant" or s == "family":
        return "variant"
    if channel == "inherit":
        if "коп" in s:
            return "copy"
        if "производ" in s or "загот" in s or "отлив" in s:
            return "derive"
        return "inherit"
    # канал db (физический состав, включая достроенную входимость)
    return "structure"


def kind_info(code):
    """Описание вида для показа (подпись, знак, цвет, стиль). Неизвестный код — `structure`."""
    return KINDS.get(code) or KINDS["structure"]


# ═══════════════════════════════════════════════════════════════════════════════════════
# ДЕКОДЕР «ИМЯ КОДАМИ» (V144, живая находка 30.10.2026)
# Проблема (владелец: «вместо имени файла выводит не понять что»): литейщики назвали файлы
# НЕ кириллицей, а UTF-16 КОДАМИ букв: `_x2_041c043e04340435043b044c_x0.asm.1`.
# Это РЕАЛЬНОЕ имя на диске (база верна!) — но человеку нечитаемо. Расшифровка:
#   041C=М 043E=о 0434=д 0435=е 043B=л 044C=ь  →  «Модель»
#   0433=г 0430=а 0439=й 043A=к         →  «гайка»
# Показ ДОЛЖЕН показывать и код, и расшифровку (не подменять данные!).
# ═══════════════════════════════════════════════════════════════════════════════════════
_HEX_RUN = re.compile(r"(?:[0-9A-Fa-f]{4})+")


def decode_name_codes(name):
    """Расшифровать блоки UTF-16-кодов в имени (`041C043E…` → «Модель»).

    Возвращает (расшифрованное_имя, признак_что_менялось). Меняем ТОЛЬКО когда получилась
    осмысленная кириллица — иначе имя возвращается БЕЗ изменений (обычные имена не трогаем!).
    """
    s = name or ""
    if not s:
        return s, False
    changed = [False]

    def _rep(m):
        t = m.group(0)
        if len(t) % 4:
            return t
        try:
            txt = "".join(chr(int(t[i:i + 4], 16)) for i in range(0, len(t), 4))
        except Exception:
            return t
        # расшифровываем ТОЛЬКО кириллицу (латиница/цифры оставляем как есть)
        if txt and all("\u0400" <= ch <= "\u04ff" or ch == " " for ch in txt):
            changed[0] = True
            return txt
        return t

    out = _HEX_RUN.sub(_rep, s)
    return out, changed[0]


def pretty_name(name):
    """Имя для ПОКАЗА: если оно записано кодами — «Код → Расшифровка»; иначе как есть."""
    dec, ok = decode_name_codes(name)
    if ok and dec != (name or ""):
        return "%s → %s" % (name, dec)
    return name or ""


def is_service(name):
    """Служебная модель (шаблон/внутренняя база) — в связях не участвует."""
    return bool(_SVC_RX.match((name or "").strip()))


def _norm(x):
    return str(x or "").strip()


def channel_of(source):
    """Канал по `links.source` — ОДНО правило на весь инструмент."""
    s = (source or "").strip().lower()
    if s == "mentions":
        return "mentions"
    if s == "family":
        return "family"
    return "db"


def load(engine_mod=None, channels=None):
    """ВСЕ СВЯЗИ ИЗ БАЗЫ — ОДИН ЗАХОД. Возвращает список словарей.

    Каждая связь: {parent, child, qty, source, channel}
      channel — из `channel_of(source)` (db / family / inherit / mentions)

    `channels` — какие каналы брать (None = ВСЕ, включая `mentions`; окна обычно просят
    без `mentions`, т.к. это не связь). Фильтр по СЛУЖЕБНЫМ применяется всегда.
    Связь = ПАРА ИМЁН (не путь!): путь лишь выбирает узел-представитель в показе.
    """
    if engine_mod is None:
        import engine as engine_mod             # noqa: F401
    want = set(channels) if channels else set(CHANNELS)
    out = []
    try:
        con = engine_mod.connect(ro=True)
    except Exception:                           # noqa: BLE001
        return out
    try:
        for par, ch, qty, src in con.execute("SELECT parent, child, qty, source FROM links"):
            a, b = _norm(par), _norm(ch)
            if not a or not b or a.lower() == b.lower():
                continue
            if is_service(a) or is_service(b):
                continue
            chn = channel_of(src)
            if chn not in want:
                continue
            out.append({"parent": a, "child": b, "qty": int(qty or 1),
                        "source": (src or ""), "channel": chn})
        if "inherit" in want:
            for ch, base, kind in con.execute("SELECT child, base, kind FROM derived"):
                a, b = _norm(ch), _norm(base)
                if not a or not b or a.lower() == b.lower():
                    continue                    # «копия от себя» — не связь
                if is_service(a) or is_service(b):
                    continue
                out.append({"parent": a, "child": b, "qty": 1,
                            "source": (kind or "наследование"), "channel": "inherit"})
    except Exception:                           # noqa: BLE001
        return out
    finally:
        try:
            con.close()
        except Exception:                       # noqa: BLE001
            pass
    return out


def children(model, engine_mod=None, sources=None, include_family=False):
    """СОСТАВ модели: [(ребёнок, сумма qty)] — ОДНО правило на весь инструмент.

    `sources` — явный список `links.source` (напр. ("family",) для исполнений).
    `include_family` — добавить исполнения в состав (по умолчанию НЕТ: они отдельным разделом).
    """
    m = _norm(model).lower()
    agg = {}
    want = None if sources is None else {str(s).lower() for s in sources}
    for e in load(engine_mod, channels=("db", "family")):
        if e["parent"].lower() != m:
            continue
        if want is not None and (e["source"] or "").lower() not in want:
            continue
        if want is None and e["channel"] == "family" and not include_family:
            continue
        agg[e["child"]] = agg.get(e["child"], 0) + e["qty"]
    return sorted(agg.items())


def parents(model, engine_mod=None, sources=None, include_family=True):
    """ВХОДИМОСТЬ модели: [(родитель, сумма qty)].

    `mentions` не входит НИКОГДА (не связь — доказано на `din931.prt.1`, грабля §74).
    """
    m = _norm(model).lower()
    agg = {}
    want = None if sources is None else {str(s).lower() for s in sources}
    for e in load(engine_mod, channels=("db", "family")):
        if e["child"].lower() != m:
            continue
        if want is not None and (e["source"] or "").lower() not in want:
            continue
        if want is None and e["channel"] == "family" and not include_family:
            continue
        agg[e["parent"]] = agg.get(e["parent"], 0) + e["qty"]
    return sorted(agg.items())


def instances(model, engine_mod=None):
    """ИСПОЛНЕНИЯ генерика (таблица семейства) — ОТДЕЛЬНО от состава.

    ДВА источника, ОДИН смысл: таблица `family` (generic→instance) и канал `family` в связях.
    Дедупликация по имени.
    """
    m = _norm(model)
    if engine_mod is None:
        import engine as engine_mod             # noqa: F401
    out, seen = [], set()
    try:
        con = engine_mod.connect(ro=True)
        try:
            for (inst,) in con.execute("SELECT instance FROM family WHERE generic=? "
                                       "ORDER BY instance", (m,)):
                if inst and inst not in seen:
                    seen.add(inst)
                    out.append((inst, 1))
        except Exception:                       # noqa: BLE001  (таблицы family может не быть)
            pass
        con.close()
    except Exception:                           # noqa: BLE001
        pass
    for e in load(engine_mod, channels=("family",)):
        if e["parent"].lower() == m.lower() and e["child"] not in seen:
            seen.add(e["child"])
            out.append((e["child"], e["qty"]))
    return out


def edges(engine_mod=None):
    """СВЯЗИ В ВИДЕ РЁБЕР ГРАФА — ОДИН ГРАФ (ДОГМА §5).

    Формат ребра (30.10.2026 — РАЗБОРЧИВЫЕ ВИДЫ):
        {from, to, type, kind, dir, origin, qty, channel}
      * `kind`   — КОД вида: structure / inherit / derive / copy / variant  (единый словарь KINDS);
      * `type`   — ЧЕЛОВЕЧЕСКАЯ ПОДПИСЬ вида («структура», «наследование», …) — для совместимости;
      * `dir`    — НАПРАВЛЕНИЕ: down (состав) · up (достроенная входимость) · base (основа);
      * `origin` — real (прочитано из файла) / built (достроено из базы);
      * `sign`/`color`/`dash` — готовые к показу знак/цвет/стиль линии.

    Тип выводится ЕДИНООБРАЗНО (`kind_code`), `mentions` в граф НЕ идёт НИКОГДА.
    """
    # 🔴🔴 V146 (владелец: «в окне "что использует" разные всякие сборки, что-то не то выводит»):
    # В СВЯЗИ попадают МАТЕРИАЛЫ и СВОЙСТВА — они не модели!
    # Живой замер `PSB`: `PTC_MASTER_MATERIAL`, `STEEL_40X`, `STEEL_45`, `LINEAR` шли как «родители».
    # Скилл дома (`SKILL_creo_read_roles.md` §7): «в `merge_base_parts` рядом с настоящей моделью
    # лежат СВОЙСТВА — это наследование СВОЙСТВА, а НЕ модели». Такие имена в граф связей НЕ идут
    # (они видны в своих таблицах: `materials`/`master_mat`/`params`).
    _junk = ("PTC_MASTER_MATERIAL", "PTC_MATERIAL_NAME", "PTC_MATERIAL_DESCRIPTION",
             "PTC_SYSTEM_MTRL_PROPS", "PTC_ASSIGNED_MATERIAL_NAME", "NONE", "NULL",
             "LINEAR", "RESTRICT_TABLE", "P_SET_DATA_ARR", "Z_SHRINK_FACTOR", "LAYERS",
             "PRO_MP_MASS", "PRO_MP_CSYS", "MAT_NAME_PTR")
    _junk_re = re.compile(r"^(STEEL|STAL|CHUGUN|AL|ALUMIN|BRONZA|LATUN|TITAN|BRASS|"
                          r"CAST_IRON|MATERIAL|MAT)([-_][0-9A-ZА-Я]*)+$", re.I)
    _an_junk_rx = re.compile(
        r"^(DISTORTION|VON MISES|STRESS|STRAIN|ENERGY|MATERIAL|MAT_NAME|DENSITY|SHRINK|"
        r"MASS PROP|PRO_MP_|MEASURE|INERTIA|VOLUME|SURFACE AREA|TEMPERATURE|PRESSURE|"
        r"FLOW|FILL TIME|COOLING)", re.I)

    def _is_junk_model(name):
        """Не модель, а МАТЕРИАЛ/СВОЙСТВО/служебное — в граф связей не пускаем."""
        n = (name or "").strip()
        if not n:
            return True
        if n.upper() in _junk:
            return True
        if _junk_re.match(n) or _an_junk_rx.match(n):
            return True
        return False

    agg = {}
    for e in load(engine_mod, channels=("db", "family", "inherit")):
        # 🔴 фильтр «не модель» — ДО построения ребра
        if _is_junk_model(e["parent"]) or _is_junk_model(e["child"]):
            continue
        ch = e["channel"]
        src = (e["source"] or "")
        k = kind_code(src, ch)
        if k == "mention":
            continue                       # упоминание — не связь (не должно прийти, страховка)
        # направление: inherit-канал читается как «основа»; достроенное — «вверх»
        if ch == "inherit":
            d = "base"
        elif src.strip().lower().startswith("built"):
            d = "up"                       # достроенная обратная входимость
        else:
            d = "down"
        key = (e["parent"], e["child"], k, d)
        agg[key] = agg.get(key, 0) + e["qty"]
    out = []
    for (a, b, k, d), q in sorted(agg.items()):
        info = kind_info(k)
        out.append({"from": a, "to": b, "type": info["label"], "kind": k, "dir": d,
                    "origin": "built" if d == "up" else "real",
                    "sign": info["sign"], "color": info["color"], "dash": info["dash"],
                    "qty": q, "channel": ("inherit" if d == "base" else "db")})
    return out


def stats(engine_mod=None):
    """СВОДКА по связям (для отчётов): сколько в каждом канале."""
    out = {c: 0 for c in CHANNELS}
    for e in load(engine_mod):
        out[e["channel"]] += 1
    return out


def check_unity(extra_allowed=()):
    """ЗАМЕР ПРИЁМКИ: есть ли ЧУЖИЕ построения связей (кроме этого модуля).

    Читает ТОЛЬКО исходники, базу НЕ трогает — можно гонять сколько угодно (диск не растёт).
    Возвращает (ok, список нарушений).
    """
    import glob
    allowed = {"plm_links.py"} | set(extra_allowed)
    bad = []
    for f in sorted(glob.glob(os.path.join(HERE, "*.py"))):
        nm = os.path.basename(f)
        if nm.startswith("_") or nm in allowed:
            continue                            # `_probe_*`/`_diag_*` — не продукт
        try:
            src = open(f, encoding="utf-8", errors="replace").read()
        except Exception:                       # noqa: BLE001
            continue
        for i, line in enumerate(src.splitlines(), 1):
            if not re.search(r"FROM\s+(links|derived)\b", line, re.I):
                continue
            if re.search(r"\bDELETE\b", line, re.I):
                continue                        # DELETE в скане — не построение
            if re.search(r"SELECT\s+COUNT", line, re.I):
                continue                        # счётчик для статистики — не построение
            bad.append("%s:%d: %s" % (nm, i, line.strip()[:95]))
    return (not bad), bad


def selfcheck(engine_mod=None, verbose=True):
    """САМОПРОВЕРКА ЕДИНСТВА (базу НЕ пишет). Возвращает (ok, отчёт)."""
    rep, ok = [], True
    rep.append("1) ПОСТРОЕНИЕ СВЯЗЕЙ — ЕДИНСТВЕННОЕ?")
    good, bad = check_unity()
    if good:
        rep.append("   ✅ чужих построений нет")
    else:
        ok = False
        rep.append("   ❌ ЧУЖИЕ ПОСТРОЕНИЯ (%d):" % len(bad))
        for b in bad[:40]:
            rep.append("      %s" % b)
    rep.append("2) КАНАЛЫ: %s" % ", ".join(CHANNELS))
    try:
        rep.append("3) БАЗА: %s" % (engine_mod.active_db() if engine_mod else "?"))
    except Exception:                           # noqa: BLE001
        rep.append("3) БАЗА: ?")
    data = load(engine_mod)
    rep.append("4) СВЯЗЕЙ ЗАГРУЖЕНО: %d" % len(data))
    selfref = [e for e in data if e["parent"].lower() == e["child"].lower()]
    empty = [e for e in data if not e["parent"] or not e["child"]]
    if selfref or empty:
        ok = False
        rep.append("   ❌ «сам с собой»: %d · пустые имена: %d" % (len(selfref), len(empty)))
    else:
        rep.append("   ✅ мусорных рёбер нет")
    st = stats(engine_mod)
    rep.append("5) ПО КАНАЛАМ: %s" % ", ".join("%s=%d" % (k, v) for k, v in sorted(st.items()))
               if data else "5) ПО КАНАЛАМ: —")
    if verbose:
        for r in rep:
            print(r)
    return ok, rep


if __name__ == "__main__":
    import sys as _sys
    if hasattr(_sys.stdout, "reconfigure"):
        try:
            _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:                       # noqa: BLE001
            pass
    try:
        import engine as _e
    except Exception as _ex:                    # noqa: BLE001
        print("engine не загрузился: %s" % _ex)
        _e = None
    _ok, _ = selfcheck(_e)
    print("САМОПРОВЕРКА СВЯЗЕЙ:", "OK" if _ok else "ЕСТЬ НАРУШЕНИЯ")
    _sys.exit(0 if _ok else 1)



