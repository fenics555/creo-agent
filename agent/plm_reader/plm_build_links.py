# -*- coding: utf-8 -*-
"""plm_build_links.py — ДОСТРОИТЕЛЬ СВЯЗЕЙ (V140, решение владельца 28.10.2026).

🔴 ЗАКОН ВЛАДЕЛЬЦА (дословно):
    «связи строятся НЕ В БАЗУ, а ПО БАЗЕ! Где-то запись связи ВНИЗ (сборки: сколько каких деталей
    входит — обратной связи НЕТ, нужно достраивать!), где-то связи ВВЕРХ (при наследовании /
    отзеркаливании / булевых операциях потомок знает родителя, а родитель НЕ В КУРСЕ — нужно
    достроить!), может каких других связей ещё не хватает!»
    «В базе данных должны быть РАЗНЫЕ КОЛОНКИ "реальные связи" и "построительные", чтобы видеть
    в случае чего, где ошибка: в чтении файлов или в построителе связей».
    «РЕАЛ можно писать в базу сразу как и все остальные параметры. А вот нужна ли для БУИЛТ
    отдельная файл-база? Может одной файл-базой обойдёмся?»  → ОДНОЙ обходимся.
    «ГЛАВНОЕ: либо одно править, либо другое!»

РАЗДЕЛЕНИЕ РАБОТ (нерушимое):
    СКАНЕР (`engine.do_scan`)      → пишет `origin='real'`  — то, что ПРОЧИТАНО В ФАЙЛЕ.
    ДОСТРОИТЕЛЬ (этот файл)        → пишет `origin='built'` — то, что ВЫВЕДЕНО ИЗ БАЗЫ.
Неверную связь правит ТОЛЬКО её автор: связь `real` = правим сканер; `built` = правим достроитель.

ЧТО ДОСТРАИВАЕТСЯ:
    1) НАСЛЕДОВАНИЕ В ОБРАТНУЮ СТОРОНУ: в файле потомок знает родителя (`MERGE_BASE_PART`,
       `ref_part_tab`) — у родителя записи НЕТ. Достраиваем: родитель → «кто от меня наследовал».
    2) ВХОДИМОСТЬ ИЗ СОСТАВА: в файле сборка знает состав (`parent → child`) — у КОМПОНЕНТА записи
       «куда я вхожу» НЕТ (владелец: «обратной связи нет»). Достраиваем: компонент → сборка.
    3) КОПИЯ/ПРОИЗВОДНАЯ — то же правило, что у наследования (обратная сторона).

ЗАПУСК:  python plm_build_links.py            — достроить (пишет в активную базу)
         python plm_build_links.py --check    — только показать объём достройки, НЕ писать
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import engine  # noqa: E402

REAL = "real"      # прочитано из файла (работа сканера)
BUILT = "built"    # выведено из базы (работа достроителя)


def _pairs(con, table, a_col, b_col, origin=None, source_like=None):
    """Пары из таблицы: (a, b) с фильтром по `origin` и `source`."""
    sql = "SELECT %s, %s FROM %s WHERE %s!='' AND %s!=''" % (a_col, b_col, table, a_col, b_col)
    args = []
    if origin:
        sql += " AND (origin IS NULL OR origin=?)"
        args.append(origin)
    if source_like:
        sql += " AND (source IS NULL OR source!=?)"
        args.append(source_like)
    return con.execute(sql, args).fetchall()


def _pairs_kind(con, table, a_col, b_col, kind_like):
    """Пары с `kind` (для `derived`): [(a, b, kind)] — ВИД связи сохраняется РАЗБОРЧИВО.

    Владелец (30.10.2026): «связи должны быть разборчивыми: зеркальное отражение / булевые
    операции / наследование… ну может только более понятно». Поэтому вид НЕ теряется:
    `наследование` · `производная` · `копия` — каждый достраивается СВОИМ обратным видом.
    """
    return con.execute(
        "SELECT %s, %s, %s FROM %s WHERE %s!='' AND %s!=''"
        % (a_col, b_col, kind_like, table, a_col, b_col)).fetchall()


# 🔴 ОБРАТНЫЕ ВИДЫ (догма владельца 30.10.2026): у КАЖДОГО вида связи есть своя обратная сторона.
# Вид читаем из базы, а не выдумываем: сканер кладёт их в `derived.kind` (проверено на базе:
# `наследование` 3 386 · `производная` 5 719 · `копия` 16 637) и в `links.source`
# (`asm_comp` 5 749 — состав сборки · `family` 15 497 — исполнения · `plm_tree` 3 606).
BACK_INHERIT = {
    "наследование": "обратное наследование",
    "производная": "обратная производная",
    "копия": "обратная копия",
    "наследование свойства": "обратное наследование свойства",
}
BACK_LINKS = {
    "asm_comp": "входимость",          # компонент знает? нет → достраиваем «в какую сборку входит»
    "family": "обратное исполнение",   # исполнение → «в какой генерик входит»
    "plm_tree": "обратное дерево PLM",
}


def build(check_only=False, engine_mod=None):
    """ДОСТРОИТЬ СВЯЗИ ПО БАЗЕ. Возвращает словарь со счётчиками (для отчёта и приёмки).

    🔴 РАСШИРЕНО 30.10.2026 (слово владельца): достраиваются ВСЕ недостающие связи ВВЕРХ и ВНИЗ,
    причём КАЖДЫЙ ВИД — СВОИМ обратным видом (`BACK_INHERIT` / `BACK_LINKS`), чтобы связь была
    РАЗБОРЧИВОЙ («зеркальное отражение / булевы операции / наследование…»). Раньше строились
    только два вида (состав + наследование) — остальные (производная, копия, исполнение, дерево PLM)
    оставались ОДНОСТОРОННИМИ, и в графе «вверх» у них не было входимости.

    Идемпотентно: если обратная пара уже есть (в любом `origin`) — не дублируем.
    Пишет ТОЛЬКО `origin='built'`; реальные строки не трогает (догма «либо одно, либо другое»).
    """
    eng = engine_mod or engine
    con = eng.connect()
    # счётчики на КАЖДЫЙ вид (разборчивость — видно, что именно достроено)
    res = {"by_kind": {}, "real_total": 0, "built_total": 0, "already": 0}
    try:
        # ── 1. НАСЛЕДОВАНИЕ/ПРОИЗВОДНАЯ/КОПИЯ: пары из `derived` с СОХРАНЕНИЕМ ВИДА.
        #    обратная пара = (base, child) с тем же видом → чтобы не путать «копия» и «наследование».
        inh = {}          # (a_low, b_low) -> kind   (child → base)
        bidir = set()     # виды, которые уже имеют встречную пару (не дублируем)
        for ch, base, kind in _pairs_kind(con, "derived", "child", "base", "kind"):
            a, b = (ch or "").strip(), (base or "").strip()
            k = (kind or "наследование").strip()
            if a and b and a.lower() != b.lower():
                inh[(a.lower(), b.lower())] = k
        res["real_total"] = len(inh)

        # ── 2. СОСТАВ: пары parent->child (кроме `built`, `mentions` — это не связь состава).
        asm = {}          # (parent_low, child_low) -> source
        for par, ch, src in con.execute(
                "SELECT parent, child, source FROM links WHERE parent!='' AND child!=''"):
            a, b = (par or "").strip(), (ch or "").strip()
            s = (src or "").strip().lower()
            if s in ("mentions",) or s.startswith("built"):
                continue                     # упоминание — не связь; built — уже достройка
            if a and b and a.lower() != b.lower():
                asm[(a.lower(), b.lower())] = s or "asm_comp"
        # какие обратные пары УЖЕ есть (реальные или достроенные)
        for (a, b) in list(asm.keys()):
            if (b, a) in asm:
                bidir.add((a, b))
        for (a, b) in list(inh.keys()):
            if (b, a) in inh:
                bidir.add((a, b))

        if check_only:
            # сколько ПАР осталось односторонними по каждому виду (без записи)
            for (a, b), k in inh.items():
                if (b, a) not in inh:
                    res["by_kind"][BACK_INHERIT.get(k, "обратное " + k)] = \
                        res["by_kind"].get(BACK_INHERIT.get(k, "обратное " + k), 0) + 1
            for (a, b), s in asm.items():
                if (b, a) not in asm:
                    t = BACK_LINKS.get(s, "входимость")
                    res["by_kind"][t] = res["by_kind"].get(t, 0) + 1
            res["already"] = len(bidir)
            return res

        # ── ДОСТРОЙКА (пишем ТОЛЬКО 'built'; реальные строки не трогаем)
        #    ВИД сохраняем: `derived.kind` = обратный вид; `links.source` = обратный вид связи.
        for (a, b) in sorted(inh):
            if (b, a) in inh or (a, b) in bidir:
                continue                     # встречная уже есть — не дублируем
            k = inh[(a, b)]
            back = BACK_INHERIT.get(k, "обратное " + k)
            con.execute("INSERT INTO derived (child,base,kind,source,origin) VALUES (?,?,?,?,?)",
                        (b, a, back, "built", BUILT))
            res["by_kind"][back] = res["by_kind"].get(back, 0) + 1
        for (a, b) in sorted(asm):
            if (b, a) in asm or (a, b) in bidir:
                continue
            s = asm[(a, b)]
            back = BACK_LINKS.get(s, "входимость")
            con.execute("INSERT INTO links (parent,child,qty,source,origin) VALUES (?,?,?,?,?)",
                        (b, a, 1, back, BUILT))
            res["by_kind"][back] = res["by_kind"].get(back, 0) + 1
        con.commit()
        res["built_total"] = con.execute(
            "SELECT COUNT(*) FROM links WHERE origin=?", (BUILT,)).fetchone()[0] + \
            con.execute("SELECT COUNT(*) FROM derived WHERE origin=?", (BUILT,)).fetchone()[0]
    finally:
        try:
            con.close()
        except Exception:
            pass
    return res


def report(res, check_only=False):
    mode = "ПРОВЕРКА (ничего не записано)" if check_only else "ДОСТРОЕНО"
    print("=== ДОСТРОИТЕЛЬ СВЯЗЕЙ — %s ===" % mode)
    print("реальных пар в базе :", res.get("real_total", 0))
    bk = res.get("by_kind") or {}
    if bk:
        print("по видам (обратные связи):")
        for k in sorted(bk):
            print("   %-34s %d" % (k, bk[k]))
    if not check_only:
        print("ВСЕГО связей 'built' в базе     :", res.get("built_total", 0))
    print()


if __name__ == "__main__":
    chk = "--check" in sys.argv
    r = build(check_only=chk)
    report(r, chk)
