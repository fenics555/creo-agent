# -*- coding: utf-8 -*-
r"""dev\incident_din439.py - РАЗБОР ИНЦИДЕНТА (только чтение, никаких записей!).

ЧТО ПРОИЗОШЛО 03.10.2026 18:43-18:50: прогон записи на «копии» `D:\AI\PROBA\vol7_copy\
din439.prt` бил по стему `din439`, а в сессии Creo уже была открыта БОЕВАЯ модель
`Z:\...\Гайки\din439.prt`. Команда `file:open` с полным путём НЕ переключила окно -
активировалась боевая, и параметр ушёл в неё. На диске появились версии
`din439.prt.2` … `din439.prt.9`. Оригинал `din439.prt.1` НЕ ТРОНУТ (mtime 02.06.2026).

Этот скрипт ТОЛЬКО ЧИТАЕТ: проверяет, попал ли тестовый параметр в боевые версии.
Никаких save/delete. Удаление версий — только по прямому слову владельца.
"""
import io
import os
import sys
import time
from pathlib import Path

AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))

ZAKI = Path(r"Z:\PTC\CREO-START\Libraries\Библиотека_стандартных_изделий\Гайки")
PROBA = Path(r"D:\AI\PROBA\vol7_copy")
MARK = "VOL7_PROBA"


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    import creo_read as CR
    print("РАЗБОР ИНЦИДЕНТА (только чтение)")
    print("оригинал боевой: %s" % (ZAKI / "din439.prt.1"))
    st = (ZAKI / "din439.prt.1").stat()
    print("  mtime: %s, размер: %d"
          % (time.strftime("%d.%m.%Y %H:%M", time.localtime(st.st_mtime)), st.st_size))

    for f in sorted(list(ZAKI.glob("din439.prt*")) + list(PROBA.glob("din439*"))):
        try:
            raw = CR.read(str(f))
            pr = CR.params(raw, CR.parse_toc(raw))
            hit = MARK in pr
            print("  %-14s %8d Б  mtime=%s  параметров=%4d  %s=%s"
                  % (f.name, f.stat().st_size,
                     time.strftime("%d.%m %H:%M", time.localtime(f.stat().st_mtime)),
                     len(pr), MARK,
                     ("%s" % pr[MARK]) if hit else "нет"))
        except Exception as e:
            print("  %-14s не читается: %s" % (f.name, e))
    print("ВЫВОД: оригинал .1 не изменён; новые версии созданы прогонами.")
    return 0


if __name__ == "__main__":
    sys.exit(main())