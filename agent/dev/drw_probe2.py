# -*- coding: utf-8 -*-
r"""dev\drw_probe2.py - РАЗВЕДКА 2: читаются ли .drw через creo_read и есть ли PDF-чертежи.

Цель: честно установить, на чём будет работать аудит чертежа (волна 6, этап 4).
Ничего не выдумывает: нет данных - пишет НЕТ ДАННЫХ с перечнем проверенного.
"""
import io
import os
import sys
import time

sys.path.insert(0, r"D:\AI\tools\agent")
import creo_read as CR   # noqa: E402

DRW_DIR = r"D:\AI\log\urn\bw\x\mbdtools\app\configuration\export\resource\templates"
PDF_ROOTS = [r"Z:\PTC\CREO-START", r"Z:\PTC\Work"]
BUDGET = 20.0


def drw_sample():
    print("ЧТЕНИЕ .drw ЧЕРЕЗ creo_read (без Creo)")
    if not os.path.isdir(DRW_DIR):
        print("  НЕТ ДАННЫХ: папки образцов нет: %s" % DRW_DIR)
        return
    names = [f for f in os.listdir(DRW_DIR) if f.lower().endswith(".drw")]
    print("  образцов в папке: %d" % len(names))
    for f in sorted(names)[:3]:
        p = os.path.join(DRW_DIR, f)
        raw = CR.read(p)
        toc = CR.parse_toc(raw)
        pr = CR.params(raw, toc)
        print("  %s: %d Б, секций %d, параметров %d"
              % (f, len(raw), len(toc), len(pr)))
        for k in sorted(pr)[:12]:
            print("      %-20s = %s" % (k, str(pr[k])[:60]))
        print("      стем по имени: %s" % CR.stem(f))
        print("      секции: %s" % ", ".join(sorted(toc)[:12]))


def pdf_sample():
    print("ПОИСК PDF-ЧЕРТЕЖЕЙ (корень: Z:)")
    t0 = time.time()
    total, shown = 0, 0
    for root in PDF_ROOTS:
        if not os.path.exists(root):
            print("  корня нет: %s" % root)
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            if time.time() - t0 > BUDGET:
                print("  бюджет поиска исчерпан (%.0f с)" % BUDGET)
                break
            for f in filenames:
                if f.lower().endswith(".pdf"):
                    total += 1
                    if shown < 8:
                        shown += 1
                        p = os.path.join(dirpath, f)
                        print("      %s (%d Б)" % (p, os.path.getsize(p)))
    print("  всего PDF найдено: %d за %.1f с" % (total, time.time() - t0))


def fitz_state():
    try:
        import fitz
        print("fitz доступен: версия %s" % getattr(fitz, "__doc__", "?")[:40].strip())
    except Exception as e:
        print("fitz НЕ доступен: %s" % e)


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    drw_sample()
    print("")
    pdf_sample()
    print("")
    fitz_state()
    return 0


if __name__ == "__main__":
    sys.exit(main())