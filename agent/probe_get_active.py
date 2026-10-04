# -*- coding: utf-8 -*-
r"""probe_get_active - ЖИВАЯ ПРОБА: что реально отдаёт file:get_active (04.10.2026).

WHY: щит ensure_active получил «активна ДРУГАЯ модель: неизвестна (?)» — значит
CREOSON отдал не тот вид ответа, что мы ждём. Не выдумываем: спрашиваем и пишем
сырой ответ в файл.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
OUT = Path(__file__).resolve().parent / "probe_get_active_out.txt"


def main():
    import creo_tools as CT
    lines = []
    j = CT.creo_call("file", "get_active", {}, 20)
    lines.append("СЫРОЙ ОТВЕТ: " + json.dumps(j, ensure_ascii=False, default=str)[:800])
    lines.append("ok() = %s" % CT.ok(j))
    lines.append("data = %r" % ((j.get("data") if isinstance(j, dict) else None),))
    lines.append("list_files: " + json.dumps(
        CT.creo_call("creo", "list_files", {"mask": "*.prt"}, 20),
        ensure_ascii=False, default=str)[:400])
    OUT.write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())