# -*- coding: utf-8 -*-
"""_check_cover.py — ПОКРЫТИЕ: сколько моделей на диске против того, что в базе.

Отвечает на вопрос «всю ли ВОРК считывает»: считает .prt/.asm/.drw файлы
по корням из настроек и сверяет с числом записей в snapshots.

Запуск: python _check_cover.py
"""
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
RE_MODEL = re.compile(r"\.(prt|asm|drw)\.\d+$", re.I)


def main():
    st = json.load(open(os.path.join(HERE, "settings", "settings.json"), encoding="utf-8"))
    roots = st.get("folders") or st.get("roots") or []
    excl = [e for e in (st.get("exclude") or []) if e]
    excl += [e for e in (st.get("exclude_folders") or []) if e]
    print("корни сканирования:")
    for r in roots:
        print("   ", r, "| есть:" if os.path.isdir(r) else "| НЕТ ДОСТУПА")
    print("исключено папок:", len(excl))
    print("глубина:", st.get("depth"), "| макс. размер МБ:", st.get("max_size_mb"))

    on_disk = {}
    total = 0
    for r in roots:
        if not os.path.isdir(r):
            continue
        n = 0
        for root, dirs, names in os.walk(r):
            if any(root.lower().startswith(e.lower()) for e in excl):
                dirs[:] = []
                continue
            for nm in names:
                if RE_MODEL.search(nm):
                    n += 1
        on_disk[r] = n
        total += n
        print("   %-24s файлов моделей: %d" % (r, n))

    try:
        import engine
        con = engine.connect()
        snap = con.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
        # сколько записей из каждого корня
        per_root = {}
        for r in roots:
            per_root[r] = con.execute(
                "SELECT COUNT(*) FROM snapshots WHERE path LIKE ?", (r + "%",)).fetchone()[0]
        con.close()
    except Exception as e:                  # noqa: BLE001
        print("база недоступна:", e)
        return 1

    print("\nна диске моделей: %d" % total)
    print("в базе snapshots : %d" % snap)
    for r, n in per_root.items():
        print("   из %-24s в базе: %d (на диске %d)" % (r, n, on_disk.get(r, 0)))
    diff = total - snap
    print("\nИТОГ: расхождение %+d (файлы без паспорта / дубли пути)" % diff)
    print("ПРИМЕЧАНИЕ: в базе хранятся ВСЕ версии файлов, если не включён 'latest_only'.")
    print("            latest_only =", st.get("latest_only"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
