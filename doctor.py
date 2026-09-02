# -*- coding: utf-8 -*-
import ast, sys, traceback
from pathlib import Path
AG = Path(__file__).resolve().parent
sys.path.insert(0, str(AG.parent)); sys.path.insert(0, str(AG))

sp = AG.parent / "settings.py"
lines = sp.read_text(encoding="utf-8").split("\n")
fixed = 0
for i, ln in enumerate(lines):
    s = ln.strip()
    if not s.startswith('("'): continue
    try:
        t = ast.literal_eval(s.rstrip(","))
    except Exception:
        continue
    if isinstance(t, tuple) and len(t) > 7 and t[3] == "list":
        good = (t[0], t[1], t[2], "list", list(t[4:-2]), t[-2], t[-1])
        lines[i] = ln[:len(ln) - len(ln.lstrip())] + repr(good) + ","
        fixed += 1
        print("[fix] строка %d: %s/%s -> список из %d" % (i + 1, t[0], t[1], len(t[4:-2])))
    elif isinstance(t, tuple) and len(t) != 7:
        print("[?] строка %d: кортеж из %d, проверь вручную" % (i + 1, len(t)))
if fixed:
    sp.write_text("\n".join(lines), encoding="utf-8")
print("исправлено кортежей:", fixed)

try:
    import importlib, settings
    importlib.reload(settings)
    bad = [r[1] for r in settings.REGISTRY if len(r) != 7]
    print("REGISTRY: записей %d, битых: %s" % (len(settings.REGISTRY), bad or "нет"))
except Exception:
    traceback.print_exc()

for m in ("creo_tools", "creo_ops_tools", "copy_tools", "diagnostic_tools",
          "learn_tools", "passport_tools", "spec_tools"):
    try:
        import importlib
        importlib.import_module(m)
        print("[+] %s: импорт ОК" % m)
    except Exception as e:
        print("[x] %s: %s" % (m, e))
print("ТЕПЕРЬ: .\\AI_RESTART.bat  (блоков должно стать 23)")