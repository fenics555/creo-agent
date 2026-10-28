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


def build(check_only=False, engine_mod=None):
    """ДОСТРОИТЬ СВЯЗИ ПО БАЗЕ. Возвращает словарь со счётчиками (для отчёта и приёмки)."""
    eng = engine_mod or engine
    con = eng.connect()
    res = {"inherit_back": 0, "asm_back": 0, "already": 0, "real_total": 0, "built_total": 0}
    try:
        # ── 1. НАСЛЕДОВАНИЕ: есть ли уже обратная пара?
        inh = set()
        for ch, base in _pairs(con, "derived", "child", "base"):
            a, b = (ch or "").strip(), (base or "").strip()
            if a and b and a.lower() != b.lower():
                inh.add((a.lower(), b.lower()))
        res["real_total"] = len(inh)
        # ── 2. СОСТАВ: пары parent->child
        asm = set()
        for par, ch in _pairs(con, "links", "parent", "child", source_like="mentions"):
            a, b = (par or "").strip(), (ch or "").strip()
            if a and b and a.lower() != b.lower():
                asm.add((a.lower(), b.lower()))
        if check_only:
            back_inh = sum(1 for (a, b) in inh if (b, a) in inh)
            back_asm = sum(1 for (a, b) in asm if (b, a) in asm)
            res["inherit_back"] = len(inh) - back_inh
            res["asm_back"] = len(asm) - back_asm
            res["already"] = back_inh + back_asm
            return res

        # ── ДОСТРОЙКА (пишем ТОЛЬКО 'built'; реальные строки не трогаем)
        for (a, b) in sorted(inh):
            if (b, a) in inh:
                continue                    # реальная/уже достроенная встречная — не дублируем
            con.execute("INSERT INTO derived (child,base,kind,source,origin) VALUES (?,?,?,?,?)",
                        (b, a, "обратное наследование", "built", BUILT))
            res["inherit_back"] += 1
        for (a, b) in sorted(asm):
            if (b, a) in asm:
                continue
            con.execute("INSERT INTO links (parent,child,qty,source,origin) VALUES (?,?,?,?,?)",
                        (b, a, 1, "built_in", BUILT))
            res["asm_back"] += 1
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
    print("достроено обратных наследования :", res.get("inherit_back", 0))
    print("достроено обратных входимости   :", res.get("asm_back", 0))
    if not check_only:
        print("ВСЕГО связей 'built' в базе     :", res.get("built_total", 0))
    print()


if __name__ == "__main__":
    chk = "--check" in sys.argv
    r = build(check_only=chk)
    report(r, chk)
