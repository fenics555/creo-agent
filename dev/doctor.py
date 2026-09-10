# -*- coding: utf-8 -*-
# DOCTOR v36 — settings: авто-сброс больше не убивает num_ctx/num_predict;
# мёртвые дефолты qwen2.5-coder:7b убраны; дефолты приведены к боевой реальности.
from pathlib import Path
AG = Path(r"D:\AI\tools\agent")
s = (AG / "settings.py").read_text(encoding="utf-8")
FAILS = []
def py_ok(t, n):
    try:
        compile(t, n, "exec"); return True
    except SyntaxError as e:
        print("[SYNTAX] %s: %s" % (n, e)); return False

REPL = [
    ('("creativity", "auto_temperature", "top_p", "num_ctx", "num_predict", "steps_max")',
     '("creativity", "auto_temperature", "top_p", "steps_max")', 0),
    ('"int", 32768,', '"int", 131072,', 1),
    ('"qwen2.5-coder:7b"', '""', 0),
    ('"minicpm-v:8b"', '"gemma4:12b"', 1),
    ('"deepseek-r1:14b"', '"gemma4:26b"', 1),
]
for old, new, cnt in REPL:
    n = s.count(old)
    if n == 0:
        print("[SKIP] не найдено: %s" % old[:44]); continue
    s = s.replace(old, new) if cnt == 0 else s.replace(old, new, cnt)
    print("[OK] %s -> %s (вхождений: %d)" % (old[:44], new[:20], n))

if py_ok(s, "settings.py"):
    (AG / "settings.py").write_text(s, encoding="utf-8")
    print("[OK] settings.py записан")
else:
    FAILS.append("compile"); print("[FAIL] компиляция, НЕ записан")

print("\n=== CHECK ===")
sx = (AG / "settings.py").read_text(encoding="utf-8")
print("сброс с num_ctx:", sx.count('"top_p", "num_ctx"'), "(ожидаю 0)")
print("32768:", sx.count("32768"), "(ожидаю 0)")
print("qwen2.5-coder:", sx.count("qwen2.5-coder"), "(ожидаю 0)")
print("num_ctx дефолт 131072:", '"int", 131072,' in sx)
print()
if FAILS: print("НЕ ПРИМЕНЕНО: " + "; ".join(FAILS))
else: print("ГОТОВО: рестарт после переноса ctl.py")