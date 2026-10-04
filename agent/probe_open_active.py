# -*- coding: utf-8 -*-
r"""probe_open_active - ЖИВАЯ ПРОБА: какой вызов file:open даёт активное окно.

WHY: `file:get_active` отдаёт пустой `data` {} — значит активной модели в сессии
нет, и щит ensure_active честно refuses. Вопрос: это из-за display:false, или
потому что CREOSON вообще не в своей сессии. Не выдумываем — перебираем режимы
открытия и пишем сырые ответы.
"""
import json
import sys
from pathlib import Path

_AGENT = Path(__file__).resolve().parent
sys.path.insert(0, str(_AGENT))
OUT = _AGENT / "probe_open_active_out.txt"

MODEL = r"D:\AI\PROBA\postregen_clean\probe_regen_20261004.prt"


def main():
    import creo_tools as CT
    p = Path(MODEL)
    lines = []

    def act(tag):
        j = CT.creo_call("file", "get_active", {}, 20)
        lines.append("%s -> get_active: %s" % (tag, json.dumps(j, ensure_ascii=False,
                                                                default=str)[:300]))

    for tag, data in (
        ("display=false activate=true", {"dirname": str(p.parent), "file": p.name,
                                         "display": False, "activate": True}),
        ("display=true activate=true", {"dirname": str(p.parent), "file": p.name,
                                        "display": True, "activate": True}),
        ("только activate", {"dirname": str(p.parent), "file": p.name, "activate": True}),
    ):
        j = CT.creo_call("file", "open", data, 40)
        lines.append("OPEN %s -> %s" % (tag, json.dumps(j, ensure_ascii=False,
                                                         default=str)[:300]))
        act(tag)

    # пост-регенерация читается по имени или полному пути?
    for f in (str(p), p.name):
        j = CT.creo_call("file", "postregen_relations_get", {"file": f}, 25)
        lines.append("postregen_get file=%s -> %s" % (
            f, json.dumps(j, ensure_ascii=False, default=str)[:300]))

    OUT.write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())