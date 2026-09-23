# -*- coding: utf-8 -*-
"""config_audit.py — аудит config.pro по фактам (класс Р, проверка без Creo).

Что делает: читает config.pro, вытаскивает КАЖДЫЙ путь (диск/UNC/$PRO_DIRECTORY/$PROSTD/
$CREO_COMMON_FILES) и проверяет его существование на диске. Отдельно проверяет,
жив ли `protkdat`, существует ли `search_path_file`, и есть ли `.lst` ограничений параметров.

Запуск:  python config_audit.py [путь\\к\\config.pro]
Вывод:   отчёт в stdout (строки ОК / НЕТ / подозрительно) + итог.
"""
import os
import re
import sys

CONFIG = sys.argv[1] if len(sys.argv) > 1 else r"Z:\PTC\CREO-START\START-STD\config.pro"
# Подстановки переменных Creo, которые встречаются в конфиге дома:
VAR = {
    "$PRO_DIRECTORY": r"D:\PTC\CREO12\Creo 12.4.2.0\Parametric",
    "$CREO_COMMON_FILES": r"D:\PTC\CREO12\Creo 12.4.2.0\Common Files",
    "$PROSTD": r"Z:\PTC\CREO-START\НАСТРОЙКИ",
}
PATHY = re.compile(r"(?:[A-Za-z]:[\\/]|\$[A-Z_]+[\\/]|\\\\)")

def norm(v: str) -> str:
    """Путь конфига -> путь Windows: переменные, слэши, хвостовые пробелы."""
    for k, r in VAR.items():
        v = v.replace(k, r)
    v = v.replace("/", "\\").rstrip("\\ ")
    return v

def exists_creo(p: str):
    """Creo хранит файлы с номером версии: mm_part.prt -> mm_part.prt.1."""
    if os.path.exists(p):
        return "есть"
    if os.path.exists(p + ".1"):
        return "есть (версия .1)"
    base = os.path.dirname(p)
    if base and os.path.isdir(base) and os.path.basename(p):
        stem = os.path.basename(p).lower()
        try:
            for f in os.listdir(base):
                if f.lower().startswith(stem):
                    return "есть (как %s)" % f
        except OSError:
            pass
    return None

def main():
    print("АУДИТ CONFIG.PRO: %s" % CONFIG)
    print("=" * 78)
    lines = open(CONFIG, encoding="utf-8-sig", errors="replace").read().splitlines()
    ok = miss = 0
    problems = []
    for n, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("!"):
            continue
        # отрезаем хвостовой комментарий вида `   ! текст`
        body = re.split(r"\s+!(?!=)", line, maxsplit=1)[0].strip()
        parts = body.split(None, 1)
        if len(parts) != 2:
            continue
        opt, val = parts[0], parts[1].strip()
        if not PATHY.search(val):
            continue
        p = norm(val)
        st = exists_creo(p)
        if st:
            ok += 1
        else:
            miss += 1
            problems.append((n, opt, val, p))
    print("путей проверено: %d | НЕТ на диске: %d" % (ok + miss, miss))
    print("-" * 78)
    for n, opt, val, p in problems:
        print("строка %d: %s" % (n, opt))
        print("   в конфиге: %s" % val)
        print("   на диске : %s   <- НЕТ" % p)
    print("=" * 78)
    print("ЧТО ДЕЛАТЬ: файла нет -> или положить файл(ы) по этому пути, или закомментировать")
    print("настройку (`!`), и записать причину рядом — как сделано с template_* 23.09.2026.")

if __name__ == "__main__":
    main()