import io
import os
import re
import sys
from pathlib import Path

import pymupdf
def notes_scan():
    """Какие плашки реально есть в читаемых эталонах - чек-лист должен опираться на факты."""
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    base = Path(r"Z:\PTC\CREO-START\Libraries\Библиотека_стандартных_изделий\Заклепки\pdf")
    marks = ["ГОСТ", "СТ", "ЛИСТ", "МАСС", "МАСШТ", "АВТОР", "ТВОР", "ПРОВЕР",
             "УТВЕРЖ", "ИНВ", "ПОДП", "ЗАМ.", "ПРИМ.", "ССЫЛ", "ИЗМ.", "ФОРМАТ", "А4", "А3"]
    for f in sorted(base.glob("*.pdf")):
        d = pymupdf.open(str(f))
        joined = " ".join(" ".join(p.get_text().split()) for p in d).upper()
        d.close()
        letters = sum(1 for ch in joined if ch.isalnum() or "Ѐ" <= ch <= "ӿ")
        ratio = letters / max(len(joined), 1)
        hits = [m for m in marks if m in joined]
        print("%-16s читаемость %3.0f%%  найдено: %s"
              % (f.name, ratio * 100, ", ".join(hits) if hits else "—"))
    return 0


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    import pymupdf
    for f in ("10299-80.pdf", "10301-80.pdf"):
        p = os.path.join(str(Path(r"Z:\PTC\CREO-START\Libraries\Библиотека_стандартных_изделий")
                            / "Заклепки" / "pdf"), f)
        d = pymupdf.open(p)
        print("=" * 70)
        print(f, "страниц:", d.page_count)
        for i, pg in enumerate(d):
            txt = " ".join(pg.get_text().split())
            print("  стр.%d: вектор %d, картинок %d, текст %d симв. -> %s"
                  % (i + 1, len(pg.get_drawings()), len(pg.get_images(full=True)),
                     len(txt), txt[:70]))
        d.close()
    return 0


def vec_scan():
    """Сколько векторных примитивов и картинок реально на страницах - порог vector_min
    должен опираться на факты, а не на догадку (иначе ложные предупреждения)."""
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    base = Path(r"Z:\PTC\CREO-START\Libraries\Библиотека_стандартных_изделий\Заклепки\pdf")
    for f in sorted(base.glob("*.pdf")):
        d = pymupdf.open(str(f))
        parts = []
        for pg in d:
            parts.append("s%d:vec%d/img%d" % (pg.number + 1, len(pg.get_drawings()),
                                             len(pg.get_images(full=True))))
        d.close()
        print("%-16s %s" % (f.name, "  ".join(parts)))
    return 0


if __name__ == "__main__":
    sys.exit(vec_scan())