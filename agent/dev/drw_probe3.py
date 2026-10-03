# -*- coding: utf-8 -*-
r"""dev\drw_probe3.py - РАЗВЕДКА 3: что реально извлекается из PDF-чертежа (fitz).

Вопросы: есть ли текст плашек, векторная штриховка, размеры. От этого зависит,
что честно умеет аудит чертежа (волна 6).
"""
import io
import sys
import time

import pymupdf as FZ   # noqa: E402

PDFS = [r"Z:\PTC\CREO-START\Libraries\Библиотека_стандартных_изделий\Заклепки\pdf\10299-80.pdf",
        r"Z:\PTC\CREO-START\Libraries\Библиотека_стандартных_изделий\Заклепки\pdf\10302-80.pdf"]


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    import pymupdf
    for p in PDFS:
        print("=" * 70)
        print(p)
        t0 = time.time()
        try:
            d = pymupdf.open(p)
        except Exception as e:
            print("  НЕ ОТКРЫВАЕТСЯ: %s" % e)
            continue
        print("  страниц: %d, %.2f с" % (d.page_count, time.time() - t0))
        pg = d[0]
        txt = pg.get_text()
        print("  текста: %d символов" % len(txt))
        for line in [x.strip() for x in txt.splitlines() if x.strip()][:30]:
            print("      | %s" % line[:90])
        try:
            drawings = pg.get_drawings()
            print("  векторных примитивов (get_drawings): %d" % len(drawings))
            kinds = {}
            for dr in drawings:
                kinds[dr.get("type", "?")] = kinds.get(dr.get("type", "?"), 0) + 1
            print("      по типам: %s" % kinds)
            pats = {}
            for dr in drawings[:4000]:
                p_ = dr.get("fill")
                if p_ is None:
                    continue
                pats[dr.get("dashes") and "dash" or "solid"] = \
                    pats.get(dr.get("dashes") and "dash" or "solid", 0) + 1
            print("      заливки: %s" % pats)
        except Exception as e:
            print("  вектор НЕ извлекается: %s" % e)
        try:
            img = pg.get_pixmap(dpi=60)
            print("  превью: %dx%d пикс." % (img.width, img.height))
        except Exception as e:
            print("  превью НЕ строится: %s" % e)
        d.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())