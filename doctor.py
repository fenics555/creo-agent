# -*- coding: utf-8 -*-
import sys, inspect
from pathlib import Path
sys.path.insert(0, r"D:\AI\tools\agent")
import scanner, settings

print("== ИСХОДНИК index_all (на диске) ==")
try: print(inspect.getsource(scanner.index_all)[:2500])
except Exception as e: print("err:", e)

print("\n== read_roots ==" , scanner.read_roots())
print("EXTS =", getattr(scanner, "EXTS", None))
print("max_file_mb =", repr(settings.get("max_file_mb")))
print("pats =", scanner._pats())

EXTS = getattr(scanner, "EXTS", set()) or set()
for r in scanner.read_roots():
    rp = Path(r)
    print("\nROOT:", r, "| exists:", rp.exists())
    if not rp.exists(): continue
    n = matched = 0; suff = {}; first_exc = None
    for f in rp.rglob("*"):
        try:
            if f.is_file():
                n += 1; s = f.suffix.lower(); suff[s] = suff.get(s, 0) + 1
                if s in EXTS and f.stat().st_size < (settings.get("max_file_mb") or 4) * 1048576 \
                   and not scanner.is_excluded(f, scanner._pats()):
                    matched += 1
        except Exception as e:
            if first_exc is None: first_exc = "%s: %s" % (type(e).__name__, e)
        if n > 30000: break
    print("  файлов:", n, "| подходят под индекс:", matched)
    print("  топ расширений:", sorted(suff.items(), key=lambda x: -x[1])[:8])
    if first_exc: print("  ПЕРВОЕ ИСКЛЮЧЕНИЕ:", first_exc)
print("\nГОТОВО: пришли вывод целиком")