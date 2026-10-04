# -*- coding: utf-8 -*-
r"""probe_disk - ПРОБА: записалось ли на ДИСК, а не только в память (04.10.2026).

WHY: прогон отчитался «пересчитано и сохранено» для 00080-03.prt, но размер и
время файла на диске НЕ изменились (12:40:54). Значит либо уравнение снято
только в памяти сессии, либо файл не тот. Выгружаем модель из памяти Creo и
читаем заново — только так видно, что лежит на диске.
"""
import json
import sys
from pathlib import Path

_AGENT = Path(__file__).resolve().parent
sys.path.insert(0, str(_AGENT))
OUT = _AGENT / "postregen_clean" / "probe_disk_out.txt"
DIR = r"D:\AI\PROBA\postregen_clean\00080"


def main():
    import time
    import creo_tools as CT
    lines = []
    # Закрываем ОКНА всех моделей сборки — иначе деталь держится в памяти.
    for name in ("00080-03.asm", "00080-03.prt", "00080-03-z.prt"):
        CT.creo_call("file", "close_window", {"file": name}, 30)
    time.sleep(2)
    CT.creo_call("file", "erase_not_displayed", {}, 30)
    time.sleep(3)
    lines.append("после закрытия всех окон — читаем с ДИСКА:")
    for name in ("00080-03.asm", "00080-03.prt", "00080-03-z.prt"):
        o = CT.creo_call("file", "open", {"dirname": DIR, "file": name,
                                          "display": False}, 60)
        r = CT.creo_call("file", "postregen_relations_get", {"file": name}, 30)
        lines.append("  %-16s -> %s" % (name, json.dumps(r, ensure_ascii=False,
                                                        default=str)[:120]))
        CT.creo_call("file", "close_window", {"file": name}, 30)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())