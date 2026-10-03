# -*- coding: utf-8 -*-
r"""dev\creo_state.py - ЧТО ЖИВЫ В CREO (диагностика перед прогоном записи)."""
import io
import json
import sys
import time
from pathlib import Path

AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))
sys.path.insert(0, str(AGENT / "batch_params"))


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    import apply as A
    import creo_tools as CT
    ready, why = A.creoson_ready()
    print("стек готов: %s (%s)" % (ready, why))
    if not ready:
        return 3
    for cmd, fn, data in (("file", "list", {}),
                          ("file", "get_active", {}),
                          ("creo", "pwd", {}),
                          ("creo", "version", {})):
        try:
            j = CT.creo_call(cmd, fn, data, 20)
            print("%s:%s -> ok=%s %s" % (cmd, fn, CT.ok(j),
                                         json.dumps(j, ensure_ascii=False,
                                                    default=str)[:400]))
        except Exception as e:
            print("%s:%s -> исключение %s" % (cmd, fn, e))
    return 0


if __name__ == "__main__":
    sys.exit(main())