# -*- coding: utf-8 -*-
r"""dev\shield_live.py - ЖИВАЯ ПРОБА ЩИТА «ТОЛЬКО КОПИЯ» (после инцидента 03.10.2026).

Ситуация как раз та, что вызвала инцидент: в сессии Creo открыта и активна БОЕВАЯ модель
`din439.prt` из Z:, а план просит записать в КОПИЮ `D:\AI\PROBA\vol7_copy\din439.prt`.
Ожидание: apply_plan ОБЯЗАН отказать (RC 4) и НЕ ЗАПИСАТЬ НИЧЕГО.
Дальше — проверка, что в боевых версиях не появилось новых файлов.
"""
import io
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))
sys.path.insert(0, str(AGENT / "batch_params"))

ZAKI = Path(r"Z:\PTC\CREO-START\Libraries\Библиотека_стандартных_изделий\Гайки")
COPY = Path(r"D:\AI\PROBA\vol7_copy\din439.prt")

fail = []


def ok(name, cond, detail=""):
    d = detail if isinstance(detail, str) else str(detail)
    print(("OK   " if cond else "FAIL ") + name + ((" | " + d) if d else ""))
    if not cond:
        fail.append(name)


def main():
    print("ЖИВАЯ ПРОБА ЩИТА «ТОЛЬКО КОПИЯ»")
    import apply as A
    ready, why = A.creoson_ready()
    ok("стек готов", ready, why)
    if not ready:
        return 3

    before = sorted(f.name for f in ZAKI.glob("din439.prt*"))

    # 1. Кто активен на самом деле
    same, why_active = A.ensure_active(str(COPY))
    ok("щит видит, что активна НЕ копия", not same, why_active)

    # 2. План из одного шага в копию, но с согласием и живым стеком
    plan = {"error": None, "steps": [{"file": str(COPY), "name": COPY.name,
                                      "param": "VOL7_SHIELD", "value": "1",
                                      "old": "", "verdict": "change", "note": ""}]}
    A.STOP["flag"] = False
    res = A.apply_plan(plan, approve=True, dry_run=False)
    ok("apply_plan отказал (RC 4), а не записал", res.get("rc") == 4,
       "RC=%s: %s" % (res.get("rc"), res.get("detail", "")[:90]))
    ok("в ответе виден щит wrong_active_model",
       res.get("shield") == "wrong_active_model", str(res.get("shield")))
    ok("ни одного успешного результата", res.get("done", 1) == 0,
       "готово: %s" % res.get("done"))

    # 3. На диске боевых версий ничего не добавилось
    after = sorted(f.name for f in ZAKI.glob("din439.prt*"))
    ok("новых боевых версий не появилось", before == after,
       "было %d, стало %d" % (len(before), len(after)))

    # 4. Параметр щита в боевых файлах отсутствует
    import creo_read as CR
    hits = []
    for f in ZAKI.glob("din439.prt*"):
        try:
            pr = CR.params(CR.read(str(f)), CR.parse_toc(CR.read(str(f))))
            if "VOL7_SHIELD" in pr:
                hits.append(f.name)
        except Exception:
            pass
    ok("тестовый параметр щита в боевых файлах не найден", not hits, ", ".join(hits))

    print("-" * 78)
    print("ИТОГ ПРОБЫ ЩИТА: %s (провалов %d)" % ("ОК" if not fail else "НЕ ОК", len(fail)))
    return 0 if not fail else 1


if __name__ == "__main__":
    sys.exit(main())