# -*- coding: utf-8 -*-
"""rules_tools.py — инструменты агента по правилам (волна 4, блок *tools).

Движок — `rules_engine.py` (общий с окном-редактором). Данные правил — `data\rules.json`.
"""
import json
import sys
from pathlib import Path

AGENT = Path(__file__).resolve().parent
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

import rules_engine as RE  # noqa: E402


def tool_rules_list(as_json=False, **kw):
    """Правила дома: сколько, по типам критериев и операциям (as_text — вид IF…THEN)."""
    doc, err = RE.load()
    if err and not doc:
        return "правила не прочитаны: %s" % err
    s = RE.stats(doc)
    if as_json:
        return {"stats": s, "rules": doc.get("rules")}
    out = ["ПРАВИЛА ДОМА (%d, включено %d; критериев %d) — %s"
           % (s["rules"], s["enabled"], s["criteria"], RE.RULES_FILE)]
    if err:
        out.append("⚠ %s" % err)
    out.append("по типам критериев: %s" % s["by_type"])
    out.append("по операциям: %s" % s["by_op"])
    out.append("-" * 70)
    for i, r in enumerate(doc.get("rules") or [], 1):
        out.append("%2d. [%s] %s (%s) — %s"
                   % (i, "вкл" if r.get("enabled", True) else "выкл",
                      r.get("id"), r.get("label"), (r.get("action") or {}).get("value", "")))
    return "\n".join(out)


def tool_rules_text(rule_id="", **kw):
    """Правила ТЕКСТОМ (IF … THEN … END_IF) — так их читает человек."""
    doc, err = RE.load()
    if err and not doc:
        return "правила не прочитаны: %s" % err
    if not rule_id:
        return RE.all_text(doc)
    r = next((x for x in (doc.get("rules") or []) if x.get("id") == rule_id), None)
    return RE.to_text(r) if r else "нет правила %r (есть: %s)" % (
        rule_id, ", ".join(x.get("id") for x in doc.get("rules") or []))


def tool_rules_check(objects_json="", rule_id="", **kw):
    """ПРОГОН правил по объектам (фактах модели).

    objects_json — JSON-список словарей-фактов, например
    '[{"parameter":"EMX_SURFACE_FUNCTION","param_value":"HOLE_BORE_FIRST"}]'.
    Пусто — пробный прогон на демонстрационных фактах, чтобы увидеть работу движка."""
    doc, err = RE.load()
    if err and not doc:
        return "правила не прочитаны: %s" % err
    if objects_json:
        try:
            objects = json.loads(objects_json)
        except Exception as e:
            return "не разобрались факты: %s (нужен JSON-список)" % e
    else:
        objects = DEMO_OBJECTS
    res = RE.run(objects, doc, only={rule_id} if rule_id else None)
    out = ["ПРОГОН ПРАВИЛ: правил %d, объектов %d, совпадений %d"
           % (res["rules"], res["objects"], len(res["hits"]))]
    for h in res["hits"]:
        out.append("  ✅ %s (%s) → объект «%s»: %s" % (h["rule"], h["label"],
                                                       h["object"], h["action"]))
    if not res["hits"]:
        out.append("  ни одно правило не совпало.")
    return "\n".join(out)


# Демонстрационные факты — чтобы движок можно было проверить без живой модели.
DEMO_OBJECTS = [
    {"parameter": "EMX_SURFACE_FUNCTION", "param_value": "HOLE_BORE_FIRST",
     "feature": "SURFACE1", "item_name": "Surface1", "feat_type": "HOLE"},
    {"parameter": "EMX_HOLE_DEPTH", "param_value": "BLIND_DEPTH",
     "feature": "HOLE2", "item_name": "Отверстие 2", "feat_type": "HOLE"},
    {"parameter": "DIA", "param_value": "85.5",
     "feature": "HOLE3", "item_name": "Отверстие 3", "feat_type": "HOLE"},
    {"item_name": "BOSS_1", "param_value": "", "group": "BOSS",
     "feature": "BOSS1", "feat_type": "PROTRUSION"},
    {"item_name": "CORE_SLIDE", "param_value": "1", "group": "SLIDER",
     "feature": "CORE1", "feat_type": "PROTRUSION"},
]

TOOLS = [
    {"name": "rules_list", "desc": "Правила дома: сколько, по типам критериев и операциям",
     "params": {"as_json": "для витрины"}, "fn": tool_rules_list,
     "kind": "read", "group": "справочник", "source": "rules_tools"},
    {"name": "rules_text", "desc": "Правила текстом IF…THEN…END_IF (пусто = все, rule_id = одно)",
     "params": {"rule_id": "id правила или пусто"}, "fn": tool_rules_text,
     "kind": "read", "group": "справочник", "source": "rules_tools"},
    {"name": "rules_check", "desc": "Прогнать правила по фактам модели (objects_json — JSON; пусто = демо-прогон)",
     "params": {"objects_json": "JSON-список фактов", "rule_id": "только это правило"},
     "fn": tool_rules_check, "kind": "check", "group": "диагностика", "source": "rules_tools"},
]