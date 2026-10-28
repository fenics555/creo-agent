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
    """СВЯЗИ В ВИДЕ РЁБЕР ГРАФА: [{from,to,type,qty,channel}] — ОДИН ГРАФ (ДОГМА §5).

    Тип ребра выводится из канала ЕДИНООБРАЗНО:
        db → «структура» (asm_comp) / «деталь»;  family → «исполнение»;
        inherit → «копия» / «производная» / «исполнение» (по `kind` из `derived`).
    `mentions` в граф НЕ идёт НИКОГДА.
    """
    agg = {}
    for e in load(engine_mod, channels=("db", "family", "inherit")):
        if e["channel"] == "db":
            typ = "структура" if (e["source"] or "").lower() == "asm_comp" else "деталь"
        elif e["channel"] == "family":
            typ = "исполнение"
        else:
            k = (e["source"] or "").lower()
            typ = "копия" if "коп" in k else ("исполнение" if "наслед" in k else "производная")
        key = (e["parent"], e["child"], typ, e["channel"])
        agg[key] = agg.get(key, 0) + e["qty"]
    return [{"from": a, "to": b, "type": t, "qty": q, "channel": ch}
            for (a, b, t, ch), q in sorted(agg.items())]


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



