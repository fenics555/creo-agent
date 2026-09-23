# -*- coding: utf-8 -*-
"""Разбор заголовков Creo-файлов: внутреннее имя модели (поле CMNM) против имени файла.
Если они расходятся — Creo не открывает модель по имени файла (XToolkitNotFound).
Только чтение, без Creo. Запуск: cmnm_scan.py <папка> [ещё папки...] [--limit N]
"""
import os
import re
import sys
import time

CREO = re.compile(r"\.(prt|asm|drw|frm|sec|lay)(\.\d+)?$", re.I)
LOG_DIR = r"D:\AI\log\cmnm_scan"


def header_name(path):
    """Внутреннее имя модели из заголовка Creo (CMNM), либо None."""
    try:
        with open(path, "rb") as f:
            raw = f.read(2048)
    except OSError:
        return None
    for enc in ("utf-8", "cp1251", "latin1"):
        try:
            head = raw.decode(enc, "ignore")
            m = re.search(r"^#-\s*CMNM\s+(.+)$", head, re.M)
            if m:
                nm = m.group(1).split("\\")[0].strip()   # в конце строки заголовка идёт «\» (перенос)
                if nm:
                    return nm
        except Exception:
            continue
    return None


def base_of(fn):
    return CREO.sub("", fn, count=1)


def main(argv):
    roots, limit = [], 0
    i = 0
    while i < len(argv):
        if argv[i] == "--limit":
            i += 1
            limit = int(argv[i])
        else:
            roots.append(argv[i].replace('"', ""))
        i += 1
    if not roots:
        print(__doc__)
        return 2
    os.makedirs(LOG_DIR, exist_ok=True)
    logp = os.path.join(LOG_DIR, "run_%s.txt" % time.strftime("%Y-%m-%d_%H%M"))
    f = open(logp, "w", encoding="utf-8")

    def out(s):
        print(s)
        f.write(s + "\n")
        f.flush()

    out("=== ВНУТРЕННИЕ ИМЕНА (CMNM) против имён файлов ===")
    total = bad = nofield = 0
    badlist = []
    t0 = time.time()
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            for fn in filenames:
                if not CREO.search(fn):
                    continue
                full = os.path.join(dirpath, fn)
                total += 1
                if limit and total > limit:
                    break
                nm = header_name(full)
                if nm is None:
                    nofield += 1
                    continue
                internal = base_of(nm.split("\\")[-1])
                filebase = base_of(fn)
                if internal.lower() != filebase.lower():
                    bad += 1
                    badlist.append((full, internal))
                    if len(badlist) <= 60:
                        out("  РАСХОЖДЕНИЕ: файл «%s»  →  внутри «%s»" % (fn, nm))
    out("\nфайлов просмотрено: %d; без поля CMNM: %d; расхождений: %d (%.0f с)" %
        (total, nofield, bad, time.time() - t0))
    if len(badlist) > 60:
        out("…и ещё %d расхождений (полный список в отчёте)" % (len(badlist) - 60))
        for full, internal in badlist[60:]:
            f.write("  %s  →  %s\n" % (full, internal))
    out("отчёт: %s" % logp)
    f.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))