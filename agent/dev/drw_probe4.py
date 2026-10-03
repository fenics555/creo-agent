# -*- coding: utf-8 -*-
r"""dev\drw_probe4.py - РАЗВЕДКА 4: постранично - текст, картинки, формат листа.

От этого зависит архитектура аудита чертежа (волна 6): если чертёж растр - штриховку
по вектору не проверить, и аудит честно говорит об этом, а не выдумывает.
"""
import io
import os
import sys
import time

import pymupdf   # noqa: E402

BASE = r"Z:\PTC\CREO-START\Libraries\Библиотека_стандартных_изделий\Заклепки\pdf"
TAKE = 3


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    names = sorted(f for f in os.listdir(BASE) if f.lower().endswith(".pdf"))[:TAKE]
    for f in names:
        p = os.path.join(BASE, f)
        print("=" * 72)
        print(f)
        t0 = time.time()
        d = pymupdf.open(p)
        for i, pg in enumerate(d):
            txt = " ".join(pg.get_text().split())
            imgs = pg.get_images(full=True)
            drw = pg.get_drawings()
            r = pg.rect
            a4 = abs(r.width - 595) < 6 and abs(r.height - 842) < 6
            print("  стр.%d: %.0fx%.0f %s | текст %d симв. | картинок %d | вектор %d"
                  % (i + 1, r.width, r.height, "A4" if a4 else "",
                     len(txt), len(imgs), len(drw)))
            if txt:
                print("      текст: %s" % txt[:160])
        d.close()
        print("  итог: %.2f с" % (time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())