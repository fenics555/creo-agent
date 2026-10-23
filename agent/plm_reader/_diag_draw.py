# -*- coding: utf-8 -*-
"""_diag_draw.py — ПОЧЕМУ ГРАФ ПУСТ. Проверка JS draw на реальных данных.

Прогоняем ТОЧНО ту же логику, что в странице: стартовый узел, два обхода,
и смотрим результат. Плюс ищем ключевой дефект: совпадают ли ключи
в ND[m].o с ключами ND (иначе обход не находит ни одного узла).

Запуск: python _diag_draw.py
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
PAGE = os.path.join(HERE, "CREO_GRAPH.html")


def main():
    h = open(PAGE, encoding="utf-8").read()
    nd = json.loads(re.search(r"const ND = (\{.*?\});\nconst ST = ", h, re.S).group(1))
    keys = set(nd)
    print("узлов:", len(keys))

    # 1. ССЫЛКИ НА НЕСУЩЕСТВУЮЩИЕ УЗЛЫ (главная причина «граф пуст»)
    miss_o = miss_n = 0
    for m, v in nd.items():
        for t in v["o"]:
            if t[0] not in keys:
                miss_o += 1
        for t in v["n"]:
            if t[0] not in keys:
                miss_n += 1
    print("ссылок в состав (o) на НЕсуществующие узлы:", miss_o)
    print("ссылок во входимость (n) на НЕсуществующие узлы:", miss_n)

    # 2. стартовый узел как в JS
    shown = sorted(nd)
    start = (next((m for m in shown if nd[m].get("m") and (nd[m]["o"] or nd[m]["n"])), None)
             or next((m for m in shown if nd[m]["o"] or nd[m]["n"]), None)
             or (shown[0] if shown else None))
    print("\nстартовый узел:", start)
    if start:
        print("   m(флаг MFG):", nd[start].get("m"), "| o:", len(nd[start]["o"]),
              "| n:", len(nd[start]["n"]))
        print("   первые o:", nd[start]["o"][:4])
        found = [t[0] for t in nd[start]["o"] if t[0] in keys]
        print("   из них СУЩЕСТВУЮТ в ND:", len(found), "шт")

    # 3. обход как в JS
    if start:
        N, L = {0: [start]}, []
        for d, key in (("d", "o"), ("u", "n")):
            seen = {start}
            frontier = [start]
            for depth in range(1, 4):
                if not frontier:
                    break
                nxt = []
                for m in frontier:
                    for t in (nd.get(m, {}).get(key) or [])[:25]:
                        nm = t[0]
                        if nm not in nd or nm == start or nm in seen:
                            continue
                        seen.add(nm)
                        N.setdefault(depth * (1 if d == "d" else -1), []).append(nm)
                        L.append((m, nm))
                        nxt.append(nm)
                frontier = nxt
        print("\nграф: узлов %d | рёбер %d" % (sum(len(v) for v in N.values()), len(L)))
        for k in sorted(N):
            print("   уровень %+d: %d" % (k, len(N[k])))

    # 4. сколько узлов вообще имеют связи, но ссылки «в пустоту»
    bad = [m for m, v in nd.items() if (v["o"] or v["n"])
           and not any(t[0] in keys for t in v["o"] + v["n"])]
    print("\nузлов, у которых ВСЕ ссылки в пустоту:", len(bad))
    if bad[:3]:
        m = bad[0]
        print("   пример:", m, "->", (nd[m]["o"] + nd[m]["n"])[:3])
    return 0


if __name__ == "__main__":
    sys.exit(main())
