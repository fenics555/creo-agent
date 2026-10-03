# -*- coding: utf-8 -*-
"""ПРИЁМКА ВОЛНЫ 4 — движок правил. Запуск:
cmd /c "cd /d D:\\AI\\tools\\agent && python -X utf8 dev\\vol4_check.py"
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))

fail = []


def ok(name, cond, detail=""):
    d = detail if isinstance(detail, str) else str(detail)
    print(("OK   " if cond else "FAIL ") + name + ((" | " + d) if d else ""))
    if not cond:
        fail.append(name)


import rules_engine as RE      # noqa: E402
import rules_tools as RT       # noqa: E402

doc, err = RE.load()
ok("rules.json прочитан без ошибок", doc is not None and not err, err or "ошибок нет")
s = RE.stats(doc)
ok("правил ≥ 8", s["rules"] >= 8, "правил: %d, критериев: %d" % (s["rules"], s["criteria"]))
ok("схема 1", doc.get("schema") == 1)

# 1. операции работают все
cases = [("equal", "5", "5", True), ("equal", "5", "6", False),
         ("unequal", "5", "6", True), ("bool", "yes", "1", True),
         ("regexp_match", "HOLE_BORE_FIRST", ".*_BORE_FIRST", True),
         ("contains", "HOLE", "THREAD", False),
         ("greater", "85.5", "60", True), ("less", "0.3", "0.5", True),
         ("less_equal", "0", "0", True), ("greater_equal", "10", "10", True)]
bad = [c for c in cases if RE._cmp(c[0], c[1], c[2]) != c[3]]
ok("все 10 операций считаются верно", not bad, str(bad))

# 2. конъюнкция: правило из двух критериев не совпадает, если один не выполнен
r2 = {"id": "t", "label": "t", "criteria": [{"type": "param_value", "op": "equal", "value": "A"},
                                           {"type": "item_name", "op": "equal", "value": "B"}]}
good, _ = RE.check_rule(r2, {"param_value": "A", "item_name": "B"})
bad2, _ = RE.check_rule(r2, {"param_value": "A", "item_name": "C"})
ok("критерии соединяются конъюнкцией (как у вендора)", good and not bad2)

# 3. цель не та — правило не срабатывает
r3 = {"id": "t3", "label": "t3", "target": {"kind": "feature", "name": "HOLE"},
      "criteria": [{"type": "param_value", "op": "equal", "value": "A"}]}
ok("цель фильтрует объекты",
   RE.check_rule(r3, {"feature": "HOLE", "param_value": "A"})[0] and
   not RE.check_rule(r3, {"feature": "RIB", "param_value": "A"})[0])

# 4. прогон на демо-фактах
res = RE.run(RT.DEMO_OBJECTS, doc)
ok("прогон находит совпадения", len(res["hits"]) >= 3,
   "совпадений: %d из %d объектов" % (len(res["hits"]), res["objects"]))

# 5. выключенное правило не срабатывает
doc2 = {"schema": 1, "rules": [dict(r, enabled=False) for r in doc["rules"]]}
ok("выключенные правила молчат", RE.run(RT.DEMO_OBJECTS, doc2)["hits"] == [])

# 6. порядок правил меняется (важен для отчёта)
doc3 = {"schema": 1, "rules": list(doc["rules"])}
before = [x["id"] for x in doc3["rules"]]
RE.move(doc3, before[0], 1)
ok("порядок правил меняется (Move UP/DOWN)", [x["id"] for x in doc3["rules"]][1] == before[0])

# 7. ТЕКСТ и ФОРМА дают одно и то же (константа 6)
txt = RE.to_text(doc["rules"][0])
ok("правило выводится текстом IF…THEN…END_IF",
   "IF " in txt and "THEN" in txt and "END_IF" in txt, txt.splitlines()[0])

# 8. валидация ловит мусор и save() его не пишет
bad_doc = {"schema": 99, "rules": [{"id": "x", "criteria": [{"type": "нет", "op": "нет"}]}]}
ok("валидация ловит чужую схему и неизвестные операции", len(RE.validate(bad_doc)) >= 3,
   str(RE.validate(bad_doc))[:100])
try:
    RE.save(bad_doc, Path(r"D:\AI\data\tmp\rules_bad.json"))
    ok("save() не пишет невалидный файл", False, "файл записан — это ошибка")
except RE.RuleError:
    ok("save() не пишет невалидный файл", True)

# 9. битый JSON → честная ошибка, а не исключение
Path(r"D:\AI\data\tmp\rules_broken.json").write_text("{ НЕ JSON", encoding="utf-8")
d3, e3 = RE.load(r"D:\AI\data\tmp\rules_broken.json")
ok("битый файл правил даёт ошибку, а не исключение", d3 is None and bool(e3), e3 or "")

# 10. инструменты агента
t1 = RT.tool_rules_list()
t2 = RT.tool_rules_check()
ok("инструменты rules_list/rules_check работают",
   "ПРАВИЛА ДОМА" in t1 and "ПРОГОН ПРАВИЛ" in t2, t2.splitlines()[0])
ok("rules_text отдаёт текст правил", "END_IF" in RT.tool_rules_text())

print("\n=== ИТОГ ВОЛНЫ 4: %s (провалов %d) ===" % ("ОК" if not fail else "НЕ ОК", len(fail)))
if fail:
    print("провалы: " + "; ".join(fail))
sys.exit(1 if fail else 0)