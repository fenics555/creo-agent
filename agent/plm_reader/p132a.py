# -*- coding: utf-8 -*-
import sys, json, os
sys.path.insert(0, r"D:\AI\tools\agent\plm_reader")
if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
import plm_reader, plm_settings

# что ЛЕЖИТ в файле настроек
sf = plm_settings.SETTINGS_FILE
print("settings.json:", sf)
raw = json.load(open(sf, encoding="utf-8")) if os.path.isfile(sf) else {}
print("ключей в файле:", len(raw))
for k in ("param_layout", "param_glue", "param_max", "param_pick"):
    print("   %-14s в файле: %r" % (k, raw.get(k, "НЕТ")))
print()
# что отдаёт load_settings_file
cfg = plm_settings.load_settings_file()
print("после load_settings_file:")
for k in ("param_layout", "param_glue", "param_max", "param_pick"):
    print("   %-14s = %r" % (k, cfg.get(k, "НЕТ")))
print()
# все ключи реестра присутствуют в cfg?
missing = [s["key"] for s in plm_settings.settings_spec_json() if s["key"] not in cfg]
print("ключей реестра НЕТ в cfg:", missing if missing else "нет — все подхватились")
