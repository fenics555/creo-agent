# -*- coding: utf-8 -*-
"""_check_page.py — приёмка PDM-Консоли: автономность, двусторонний обход, цвета.

Запуск: python _check_page.py
"""
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
    if not os.path.isfile(PAGE):
        print("НЕТ ФАЙЛА: сначала соберите страницу (кнопка PDM-Консоль)")
        return 1
    h = open(PAGE, encoding="utf-8").read()
    print("размер: %d КБ" % (len(h) // 1024))
    print("внешних ресурсов (CDN):", len(re.findall(r"https?://", h)) or "0 — автономно")
    print("двусторонний обход:", 'go(root, "d")' in h and 'go(root, "u")' in h)
    cols = ["main-down", "main-up", "deep-down", "deep-up", "base", "copy"]
    print("цвета связей:", {c: (c in h) for c in cols})
    print("перегородки:", "vgrip" in h and "hgrip" in h)
    print("фикс. высота карточки:", "height:230px" in h)
    print("миниатюры 40px:", "max-width:40px" in h)
    lit = [l for l in ("__DATA__", "__STATS__", "__MEDIA__") if l in h]
    print("остатки литералов:", lit or "нет — ок")
    return 0


if __name__ == "__main__":
    sys.exit(main())
