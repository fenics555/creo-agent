# -*- coding: utf-8 -*-
r"""
АГЕНТ v12 — БЛОК ПАСПОРТА (passport_tools.py)
Живой паспорт компании: собирает config.pro через CREOSON,
перезаписывает Creo/SKILL_company_config.md (агент ищет его через search_kb).
"""
import datetime, hashlib
import core
import creo_tools as CT

KEYS = ["pro_unit_sys", "pro_unit_length", "pro_unit_mass", "default_dec_places",
        "tolerance_standard", "initial_bend_y_factor", "drawing_setup_file",
        "start_model_dir", "search_path", "trail_dir",
        "template_solidpart", "template_designasm"]
OUT = core.REPO / "Creo" / "SKILL_company_config.md"

def _collect():
    vals = {}
    for k in KEYS:
        j = CT.creo_call("creo", "get_config", {"name": k}, 10)
        v = ((j or {}).get("data") or {}).get("values") or []
        if v: vals[k] = v[0]
    return vals

def _write(vals):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    h = hashlib.md5("\n".join("%s=%s" % kv for kv in sorted(vals.items())).encode()).hexdigest()
    lines = ["---", "name: company-config", "system: Creo", "priority: high", "---",
             "ПАСПОРТ КОМПАНИИ (сбор %s)" % datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
             "Единицы, допуски, ключевое:"]
    lines += ["%s = %s" % (k, v) for k, v in vals.items()]
    lines += ["hash: " + h]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    return h

def tool_show(**kw):
    vals = _collect()
    if not vals: return "не смог получить конфиг: Creo/CREOSON молчат"
    h = _write(vals)
    return "ПАСПОРТ (живой сбор):\n" + "\n".join("• %s = %s" % kv for kv in vals.items()) + "\n(сохранён в Creo/SKILL_company_config.md, hash %s)" % h[:8]

def tool_refresh(**kw):
    return tool_show()

TOOLS = [
    {"name": "passport_show", "desc": "Живой паспорт компании: единицы, допуски, пути, шаблоны из config.pro", "params": {}, "approval": False, "fn": tool_show},
    {"name": "passport_refresh", "desc": "Пересобрать паспорт компании и перезаписать скилл", "params": {}, "approval": False, "fn": tool_refresh},
]