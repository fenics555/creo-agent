# -*- coding: utf-8 -*-
r"""probe_write_shield - ПРОБА щита записи (аудит 04.10.2026).

ЗАЧЕМ: запрет «на Z: только чтение» был только в словах. Проверяем КОД: скормить
apply_plan план с сетевым путём и с локальным и убедиться, что сетевой
отклонён (RC 5), а локальный дошёл до проверки согласия. Записи в Creo здесь
не происходит: до стека дело не доходит.
"""
import json
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parent / "postregen_clean"
sys.path.insert(0, str(TOOL))
sys.path.insert(0, str(TOOL.parent))
OUT = TOOL / "probe_write_shield_out.txt"


def main():
    import plan as P
    import apply as A
    lines = []

    lines.append("адрес CREOSON из настроек: %s" % (P.creoson_url(),))
    lines.append("запрещённые корни: %s" % (P.FORBIDDEN_ROOTS,))
    for raw in (r"Z:\PTC\Work\00080\sborka.asm",
                r"Y:\Public\sborka.asm",
                r"\\server\share\model.asm",
                r"D:\AI\PROBA\postregen_clean\probe_regen_20261004.prt",
                r"X:\net\model.asm"):
        ok, why = P.write_allowed(raw)
        lines.append("write_allowed(%s) -> %s | %s" % (raw, ok, why))

    # План с ЗАПРЕЩЁННОЙ целью: должен быть отказ ДО согласия и до стека.
    bad = {"steps": [{"file": r"Z:\PTC\Work\00080\sborka.asm", "name": "sborka.asm",
                      "kind": "postregen", "target": "1 уравнений",
                      "verdict": "clear", "note": ""}]}
    r = A.apply_plan(bad, approve=True)
    lines.append("план с сетевой целью: RC %s — %s" % (r.get("rc"), r.get("detail")))

    # План с ЛОКАЛЬНОЙ целью: щит пропускает, дальше срабатывает согласие/стек.
    good = {"steps": [{"file": r"D:\AI\PROBA\postregen_clean\probe_regen_20261004.prt",
                       "name": "probe_regen_20261004.prt", "kind": "postregen",
                       "target": "1 уравнений", "verdict": "clear", "note": ""}]}
    r2 = A.apply_plan(good, approve=False)
    lines.append("локальная цель без согласия: RC %s — %s" % (r2.get("rc"), r2.get("detail")))
    r3 = A.apply_plan(good, approve=True, dry_run=True)
    lines.append("локальная цель dry_run: RC %s — %s" % (r3.get("rc"), r3.get("detail")))

    OUT.write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())