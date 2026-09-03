# -*- coding: utf-8 -*-
import re
def _txt(name):
    try:
        import tools_registry as TR
        t = TR.get(name); return str(t["fn"]()) if t else ""
    except Exception: return ""
def tool_trail_predict(top=10, **kw):
    trend = _txt("trail_trend"); prob = _txt("trail_problems")
    rows = []
    for m in re.finditer(r"МЕДЛЕННЫЕ ОТКРЫТИЯ\s*/\s*(.+?)\s*—\s*(\d+)\s*сек[^—]*?за\s*(\d+)\s*случ", trend):
        rows.append((int(m.group(2)) * int(m.group(3)), m.group(1).strip(), int(m.group(2)), int(m.group(3)), "медленные открытия"))
    rows.sort(key=lambda x: -x[0])
    if not rows: return "нет данных для прогноза"
    out = ["ПРОГНОЗ ДЕГРАДАЦИИ (риск = сек × случаев):"]
    for score, name, sec, cnt, kind in rows[:int(top or 10)]:
        out.append("⚠ %s — %s: %d сек × %d = %d" % (name, kind, sec, cnt, score))
    out.append("Рекомендация: purge версий, упрощение регенерации.")
    return "\n".join(out)
TOOLS = [{"name": "trail_predict", "desc": "Прогноз деградации моделей", "params": {"top": "строк"}, "approval": False, "fn": tool_trail_predict}]
