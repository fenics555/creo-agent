# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"D:\AI\tools\agent\plm_reader")
if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
import plm_reader, plm_settings
spec = plm_settings.settings_spec_json()
print("всего настроек в реестре:", len(spec))
groups = {}
for s in spec:
    groups.setdefault(s["group"], []).append(s["key"])
for g, keys in groups.items():
    print("  %-12s %d: %s" % (g, len(keys), ", ".join(keys)))
print()
print("группа ПАРАМЕТРЫ:")
for s in spec:
    if s["group"] == "ПАРАМЕТРЫ":
        print("   ", s)
