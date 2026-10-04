# -*- coding: utf-8 -*-
r"""probe_named_read - ПРОБА: под каким именем читается версионированная сборка.

WHY: на Z: лежит `00080-03.asm.1`. И с `.1`, и без `.1` CREOSON отвечает
«Unknown Model Extension». Не гадаем — перебираем варианты и печатаем СЫРОЙ
ответ на каждый. Только чтение, записи нет.
"""
import json
import sys
from pathlib import Path

_AGENT = Path(__file__).resolve().parent
sys.path.insert(0, str(_AGENT))
OUT = _AGENT / "postregen_clean" / "probe_named_read_out.txt"
DIR = r"Z:\PTC\Work\00080"


def main():
    import creo_tools as CT
    lines = []
    variants = ["00080-03.asm.1", "00080-03.asm", "00080-03", "00080-03.PRT"]
    for name in variants:
        o = CT.creo_call("file", "open", {"dirname": DIR, "file": name,
                                         "activate": True}, 60)
        lines.append("OPEN %-16s -> %s" % (name, json.dumps(o, ensure_ascii=False,
                                                            default=str)[:200]))
        if CT.ok(o):
            g = CT.creo_call("file", "get_active", {}, 20)
            lines.append("   активная: %s" % json.dumps(g, ensure_ascii=False,
                                                        default=str)[:200])
            r = CT.creo_call("file", "postregen_relations_get", {"file": name}, 30)
            lines.append("   postregen(%s) -> %s" % (name, json.dumps(r, ensure_ascii=False,
                                                                      default=str)[:200]))
    OUT.write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())