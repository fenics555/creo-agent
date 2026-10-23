# -*- coding: utf-8 -*-
"""_diag_graph.py — ДИАГНОСТИКА PDM-Консоли: картинки и граф.

1) Картинки: сколько узлов ссылаются на файл, которого НЕТ на диске.
2) Граф: воспроизводим алгоритм draw на реальных данных (на Python), смотрим,
   строится ли он и почему может быть пусто.

Запуск: python _diag_graph.py
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "CREO_GRAPH.html")
MEDIA = os.path.join(HERE, "db", "media")


def main():
    h = open(PAGE, encoding="utf-8").read()
    nd = json.loads(re.search(r"const ND = (\{.*?\});\nconst ST = ", h, re.S).group(1))
    st = json.loads(re.search(r"const ST = (\{.*?\});\n", h, re.S).group(1))
    print("узлов:", len(nd), "| cfg:", st.get("cfg"))

    # --- 1. КАРТИНКИ ---
    with_img = [m for m, v in nd.items() if v.get("i")]
    missing = [m for m in with_img if not os.path.isfile(os.path.join(MEDIA, nd[m]["i"]))]
    exts = Counter(v["i"].rsplit(".", 1)[-1] for m, v in nd.items() if v.get("i"))
    print("\n--- КАРТИНКИ ---")
    print("узлов с ссылкой на превью:", len(with_img), "| файлов в media:",
          len(os.listdir(MEDIA)) if os.path.isdir(MEDIA) else 0)
    print("ссылок на НЕсуществующий файл:", len(missing))
    if missing[:5]:
        for m in missing[:5]:
            print("   нет файла:", nd[m]["i"], "для", m)
    print("расширения:", dict(exts))

    # --- 2. ГРАФ ---
    print("\n--- ГРАФ (воспроизведение алгоритма draw) ---")
    with_links = [m for m, v in nd.items() if v["o"] or v["n"]]
    print("узлов со связями:", len(with_links), "из", len(nd))
    if not with_links:
        print("!! ГРАФ ПУСТ: ни у одного узла нет связей — рисуется пустая область")
        return 1
    # стартовый узел: как в JS (MFG со связями -> любой со связями)
    start = next((m for m in sorted(nd) if nd[m].get("m") and (nd[m]["o"] or nd[m]["n"])), None)
    start = start or sorted(with_links)[0]
    print("стартовый узел:", start, "| o:", len(nd[start]["o"]), "| n:", len(nd[start]["n"]))
    # обход как в JS
    depth_max = (st.get("cfg") or {}).get("graph_depth", 3)
    node_max = (st.get("cfg") or {}).get("graph_nodes_max", 120)
    child_max = (st.get("cfg") or {}).get("graph_children_max", 25)
    N, L = {0: [start]}, []
    for d, key in (("d", "o"), ("u", "n")):
        seen = {start}
        frontier = [start]
        for depth in range(1, depth_max + 1):
            if not frontier:
                break
            nxt = []
            for m in frontier:
                if sum(len(v) for v in N.values()) > node_max:
                    break
                for t in (nd.get(m, {}).get(key) or [])[:child_max]:
                    nm = t[0]
                    if nm not in nd or nm == start or nm in seen:
                        continue
                    seen.add(nm)
                    N.setdefault(depth * (1 if d == "d" else -1), []).append(nm)
                    L.append((m, nm))
                    nxt.append(nm)
            frontier = nxt
    print("узлов в графе:", sum(len(v) for v in N.values()), "| рёбер:", len(L))
    for k in sorted(N):
        print("   уровень %+d: %d" % (k, len(N[k])))
    if len(L) == 0:
        print("!! ГРАФ БЕЗ РЁБЕР: стартовый узел без связей")
    return 0


if __name__ == "__main__":
    sys.exit(main())
