# -*- coding: utf-8 -*-
"""Волна 1, Задача А — приёмка типов инструментов (живой прогон).
Запуск: cmd /c "cd /d D:\AI\tools\agent && python -X utf8 dev\vol1_check.py > D:\AI\data\tmp\vol1_a.txt 2>&1"
Приёмка: kind=check даёт список, tools_card печатает сводку, 162 старых инструмента на месте.
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tools_registry as TR          # noqa: E402
import help_tools as HT              # noqa: E402

fail = []


def chk(name, cond, detail=""):
    print(("OK   " if cond else "FAIL ") + name + ((" | " + detail) if detail else ""))
    if not cond:
        fail.append(name)


# 1. реестр цел: старые инструменты на месте (+18 = tools_card, prog_contract, hol_check,
#    hol_report, rules_list, rules_text, rules_check, checks_list, checks_run, checks_report,
#    drawing_audit, drawing_report, batch_params_plan, batch_params_apply, feature_rename_plan,
#    plan_build, plan_run, plan_report — волна 8)
# ЧИСЛА СТАРЕЮТ КАЖДЫЙ ХОД (грабля волн 6-7): пересчитаны 03.10.2026 живым прогоном.
TOTAL = len(TR.TOOLS)
chk("реестр: 185 инструментов (180 волн 1–8 + 5 моста к чесалке)", TOTAL == 185,
    "фактически %d" % TOTAL)
chk("реестр: 53 блока (52 + harvest_reader_tools — мост к базе чесалки)",
    len(TR.BLOCKS) == 53,
    "фактически %d" % len(TR.BLOCKS))

# 2. карта: все инструменты получили тип, ни один не «other»
kinds = {}
others = []
for k, g, t in TR.iter_tools():
    kinds[k] = kinds.get(k, 0) + 1
    if k == "other":
        others.append(t["name"])
chk("карта: все размечены, other=0", not others,
    "other=%d %s" % (len(others), others[:8]))
print("     сводка по kind: %s" % kinds)

# 3. kind=check даёт непустой список
res_chk = HT.tool_tools_help(kind="check")
chk("tools_help(kind=check) печатает список",
    isinstance(res_chk, str) and res_chk.startswith("- ") and len(res_chk.splitlines()) >= 1,
    "строк: %d" % len(res_chk.splitlines()))
print(res_chk[:600])

# 4. явное поле TOOLS побеждает разметку по блоку
card_txt = TR.card()
chk("tools_card печатает сводку по типам", "ПО ТИПУ" in card_txt and "ПО ПРЕДМЕТУ" in card_txt)
print(card_txt[:900])

# 5. фильтр по предмету
res_pdf = HT.tool_tools_help(group="PDF")
chk("tools_help(group=PDF) непуст", res_pdf.startswith("- "), "строк: %d" % len(res_pdf.splitlines()))

# 6. needs_creo проставлен у Creo-блоков
list(TR.iter_tools())          # наполняет карту типов
creo = [t["name"] for k, g, t in TR.iter_tools() if TR.meta_of(t["name"])[2]]
chk("needs_creo=True есть у Creo-инструментов", len(creo) > 0, "инструментов: %d" % len(creo))

# 7. старый вызов без kind работает (обратная совместимость)
old = HT.tool_tools_help()
chk("tools_help() без фильтра печатает все", len(old.splitlines()) == TOTAL,
    "строк: %d, ожидалось %d" % (len(old.splitlines()), TOTAL))

print("=== ИТОГ: %s (провалов %d) ===" % ("ОК" if not fail else "НЕ ОК", len(fail)))
sys.exit(1 if fail else 0)