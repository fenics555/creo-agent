# -*- coding: utf-8 -*-
"""_diag_front.py — проверка ФРОНТЕНДА (картинки + граф) без браузера.

Смотрим: 1) путь IMG в собранной странице; 2) наличие файлов по этому пути;
3) размер первых превью (реально ли это картинки); 4) подозрительные места JS.

Запуск: python _diag_front.py
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
    m = re.search(r"const IMG = ([^;]+);", h)
    print("IMG =", m.group(1) if m else "НЕТ")
    nd = json.loads(re.search(r"const ND = (\{.*?\});\nconst ST = ", h, re.S).group(1))
    st = json.loads(re.search(r"const ST = (\{.*?\});\n", h, re.S).group(1))
    print("stats.media:", st.get("media"), "| узлов:", st.get("nodes"), "| рёбер:", st.get("edges"))

    # путь IMG -> реальная папка
    imgval = m.group(1).strip().strip('"') if m else ""
    base = imgval.rstrip("/")
    real = os.path.normpath(os.path.join(HERE, base))
    print("папка по IMG:", real, "| есть:", os.path.isdir(real))

    withimg = [v["i"] for v in nd.values() if v.get("i")]
    ok = miss = 0
    sizes = []
    for f in withimg[:400]:
        p = os.path.join(real, f)
        if os.path.isfile(p):
            ok += 1
            sizes.append(os.path.getsize(p))
        else:
            miss += 1
    print("проверено 400 ссылок: есть %d | нет %d" % (ok, miss))
    if sizes:
        sizes.sort()
        print("размеры превью: мин %d, медиана %d, макс %d байт"
              % (sizes[0], sizes[len(sizes) // 2], sizes[-1]))

    # JS: ищем рискованные места
    js = re.search(r"<script>(.*)</script>", h, re.S).group(1)
    print("\n--- ПОДОЗРИТЕЛЬНОЕ В JS ---")
    for pat, note in ((r'shown\[0\]', "стартовый узел может быть без связей"),
                      (r"ND\[m\]\.o\.length", "у узла может не быть o/n"),
                      (r"\.find\(m => ND\[m\]\.m", "поиск MFG"),
                      (r"document\.querySelectorAll\(.#graph \.nd.\)", "слушатели узлов")):
        print("   %-42s %s" % (pat, js.count(pat.replace("\\", "")) or 0))

    # ключевая проверка: есть ли одиночка-стартовый
    no_links = [k for k, v in nd.items() if not v["o"] and not v["n"]]
    print("\nузлов БЕЗ связей:", len(no_links), "из", len(nd))
    f2 = sorted(k for k, v in nd.items() if v["o"] or v["n"])
    print("первый узел СО связями (порядок словаря):", f2[0] if f2 else "нет")
    return 0


if __name__ == "__main__":
    sys.exit(main())
