# -*- coding: utf-8 -*-
"""Разбор заголовков Creo-файлов: внутреннее имя модели (поле CMNM) против имени файла.
Если они расходятся — Creo не открывает модель по имени файла (XToolkitNotFound).
Только чтение, без Creo. Запуск: cmnm_scan.py <папка> [ещё папки...] [--limit N]
"""
import os
import re
import sys
import time

# Печать делаем кодировко-устойчивой: в cp1251 нет стрелки «→» (живая находка 23.09.2026).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CREO = re.compile(r"\.(prt|asm|drw|frm|sec|lay)(\.\d+)?$", re.I)
LOG_DIR = r"D:\AI\log\cmnm_scan"


def strip_len_prefix(nm):
    """Внутреннее имя в заголовке идёт с 3-значным HEX-префиксом длины:
    «007d25.asm» = 7 символов «d25.asm», «00bplatina.prt» = 11 «platina.prt».
    Живая находка 23.09.2026: без этой правки программа показывала ЛОЖНОЕ расхождение
    на каждом файле (7 из 7 на пробной папке), потому что префикс считался частью имени.
    Оставляем строку как есть, если префикс не сходится по длине или это не похоже на имя файла."""
    m = re.match(r"^([0-9a-fA-F]{3})(.+)$", nm)
    if m:
        ln = int(m.group(1), 16)
        rest = m.group(2)
        if abs(len(rest) - ln) <= 1 and "." in rest:
            return rest
    return nm


def header_name(path, raw=False):
    """Внутреннее имя модели из заголовка Creo (CMNM), либо None.
    raw=True — как записано в файле (с префиксом длины)."""
    try:
        with open(path, "rb") as f:
            raw_bytes = f.read(2048)
    except OSError:
        return None
    for enc in ("utf-8", "cp1251", "latin1"):
        try:
            head = raw_bytes.decode(enc, "ignore")
            m = re.search(r"^#-\s*CMNM\s+(.+)$", head, re.M)
            if m:
                nm = m.group(1).split("\\")[0].strip()   # в конце строки заголовка идёт «\» (перенос)
                if nm:
                    return nm if raw else strip_len_prefix(nm)
        except Exception:
            continue
    return None


def base_of(fn):
    return CREO.sub("", fn, count=1)


def scan(roots, limit=0, progress=None):
    """Обход и сверка внутреннего имени с именем файла. НИЧЕГО не печатает и не пишет —
    точка входа для окна программы.
    Возвращает: {'files': N, 'nofield': M, 'bad': [(полный путь, внутреннее имя, имя файла), ...],
                 'seconds': сек}
    Дефекты, найденные при переносе в окно (23.09.2026):
      * прежний `--limit` останавливал только внутренний цикл по файлам и продолжал обход папок;
      * стрелка «→» в отчёте роняла печать на cp1251-консоли (лечится `-X utf8`/reconfigure в main).
    """
    def say(s):
        if progress:
            progress(s)

    total = nofield = 0
    bad = []
    t0 = time.time()
    for root in roots:
        for dirpath, _dirnames, filenames in os.walk(root):
            for fn in filenames:
                if not CREO.search(fn):
                    continue
                full = os.path.join(dirpath, fn)
                total += 1
                nm = header_name(full)
                if nm is None:
                    nofield += 1
                    continue
                internal = base_of(nm.split("\\")[-1])
                filebase = base_of(fn)
                if internal.lower() != filebase.lower():
                    bad.append((full, nm, fn))
                    say("РАСХОЖДЕНИЕ: %s" % fn)
                if limit and total >= limit:
                    return {"files": total, "nofield": nofield, "bad": bad, "seconds": time.time() - t0}
    return {"files": total, "nofield": nofield, "bad": bad, "seconds": time.time() - t0}


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
    res = scan(roots, limit)
    for full, nm, fn in res["bad"][:60]:
        out("  РАСХОЖДЕНИЕ: файл «%s»  →  внутри «%s»" % (fn, nm))
    out("\nфайлов просмотрено: %d; без поля CMNM: %d; расхождений: %d (%.0f с)" %
        (res["files"], res["nofield"], len(res["bad"]), res["seconds"]))
    if len(res["bad"]) > 60:
        out("…и ещё %d расхождений (полный список в отчёте)" % (len(res["bad"]) - 60))
        for full, nm, _fn in res["bad"][60:]:
            f.write("  %s  →  %s\n" % (full, nm))
    out("отчёт: %s" % logp)
    f.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))