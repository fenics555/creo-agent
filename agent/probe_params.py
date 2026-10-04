# -*- coding: utf-8 -*-
r"""probe_params - ПРОБА: какие параметры есть и какие удаляются (04.10.2026).

WHY: маска PTC_* вернула RC 1 — «Could not delete parameter PTC_MASTER_MATERIAL».
Похоже, системные параметры не удаляются (ожидаемо). Чтобы доказать, что
удаление пользовательских параметров РАБОТАЕТ, нужен параметр, который удалить
можно. Список имён — в файл, ничего не пишем.
"""
import json
import sys
from pathlib import Path

_AGENT = Path(__file__).resolve().parent
sys.path.insert(0, str(_AGENT))
OUT = _AGENT / "postregen_clean" / "probe_params_out.txt"
MODEL = r"D:\AI\PROBA\postregen_clean\probe_regen_20261004.prt"


def main():
    import creo_tools as CT
    lines = []
    p = Path(MODEL)
    CT.creo_call("file", "open", {"dirname": str(p.parent), "file": p.name,
                                  "activate": True}, 40)
    j = CT.creo_call("parameter", "list", {"file": str(MODEL)}, 30)
    d = (j.get("data") or {}).get("paramlist") or []
    for x in d:
        if isinstance(x, dict) and x.get("name"):
            lines.append("%s = %s" % (x.get("name"), x.get("value")))
    lines.append("ВСЕГО ПАРАМЕТРОВ: %d" % len(lines))
    OUT.write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())