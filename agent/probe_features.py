# -*- coding: utf-8 -*-
r"""probe_features - ПРОБА: какие элементы модели есть для проверки переименования.

WHY: маска CS* не нашла ни одного элемента. Чтобы проверить feature:rename на
живой модели, нужен реальный элемент. Список — в файл, ничего не пишем.
"""
import json
import sys
from pathlib import Path

_AGENT = Path(__file__).resolve().parent
sys.path.insert(0, str(_AGENT))
OUT = _AGENT / "postregen_clean" / "probe_features_out.txt"
MODEL = r"D:\AI\PROBA\postregen_clean\probe_regen_20261004.prt"


def main():
    import creo_tools as CT
    lines = []
    p = Path(MODEL)
    CT.creo_call("file", "open", {"dirname": str(p.parent), "file": p.name,
                                  "activate": True}, 40)
    for tag, data in (("все", {"file": str(MODEL), "paths": True}),
                      ("с именами", {"file": str(MODEL), "inc_unnamed": False})):
        j = CT.creo_call("feature", "list", data, 30)
        d = (j.get("data") or {}).get("featlist") or []
        lines.append("--- %s: %d элементов" % (tag, len(d)))
        for x in d[:40]:
            if isinstance(x, dict):
                lines.append("  %s | %s | %s" % (x.get("name"), x.get("type"),
                                                 x.get("status")))
    OUT.write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())