# -*- coding: utf-8 -*-
# DOCTOR v25 — A) сброс кэша промта в /setcfg; B) num_ctx в options; C) think в запросе;
# D) дефолт окна контекста 32768 (регистр, диапазон ползунка до 65536, значение в config).
# ЗАПУСК ОДИН РАЗ: python doctor.py   ПОТОМ: .\AI_RESTART.bat + Ctrl+F5
import json, re
from pathlib import Path

AG = Path(r"D:\AI\tools\agent")
FAILS = []; SKIPS = []

def py_ok(t, n):
    try:
        compile(t, n, "exec"); return True
    except SyntaxError as e:
        print("[SYNTAX] %s: %s" % (n, e)); return False

a = (AG / "agent.py").read_text(encoding="utf-8")

# --- A: инвалидация _SYS_CACHE в /setcfg ---
old_a = 'settings.set_val(b.get("key"), b.get("value")); self._j({"ok": True})'
new_a = 'settings.set_val(b.get("key"), b.get("value")); _SYS_CACHE.clear(); self._j({"ok": True})'
if "_SYS_CACHE.clear()" in a:
    SKIPS.append("A"); print("[SKIP] A: уже есть")
elif old_a in a:
    a = a.replace(old_a, new_a, 1); print("[OK] A: _SYS_CACHE.clear() в /setcfg")
else:
    FAILS.append("A"); print("[FAIL] A: якорь не найден")

# --- B: num_ctx в options обеих ветвей beh() ---
old_b1 = '"num_predict": int(settings.get("num_predict") or 1536)}, steps)'
new_b1 = '"num_predict": int(settings.get("num_predict") or 1536), "num_ctx": int(settings.get("num_ctx") or 32768)}, steps)'
old_b2 = '"num_predict": int(settings.get("num_predict") or 1024)}, steps)'
new_b2 = '"num_predict": int(settings.get("num_predict") or 1024), "num_ctx": int(settings.get("num_ctx") or 32768)}, steps)'
if a.count('"num_ctx": int(settings.get("num_ctx")') >= 2:
    SKIPS.append("B"); print("[SKIP] B: уже есть")
else:
    okb = True
    if old_b1 in a: a = a.replace(old_b1, new_b1, 1)
    else: okb = False; FAILS.append("B1"); print("[FAIL] B: якорь 1536 не найден")
    if old_b2 in a: a = a.replace(old_b2, new_b2, 1)
    else: okb = False; FAILS.append("B2"); print("[FAIL] B: якорь 1024 не найден")
    if okb: print("[OK] B: num_ctx в обеих ветвях beh()")

# --- C: параметр think в запросе /api/chat ---
anc_c = 'if invalid_cnt: use_opts = dict(use_opts, temperature=0)'
old_c = '"stream": False, "options": use_opts, "messages": messages}, t=600)'
new_c = '"stream": False, "think": _thk, "options": use_opts, "messages": messages}, t=600)'
thk = '_thk = int(settings.get("think_mode") or 0) > 0 and (settings.model_for("chat") or "").startswith(("qwen3", "deepseek"))'
if '"think": _thk' in a:
    SKIPS.append("C"); print("[SKIP] C: уже есть")
elif anc_c in a and old_c in a:
    i = a.index(anc_c); ls = a.rfind("\n", 0, i) + 1; ind = a[ls:i]
    a = a.replace(anc_c, anc_c + "\n" + ind + thk, 1)
    a = a.replace(old_c, new_c, 1)
    print("[OK] C: think в запросе (qwen3/deepseek, по think_mode)")
else:
    FAILS.append("C"); print("[FAIL] C: якоря не найдены")

if not FAILS:
    if py_ok(a, "agent.py"):
        (AG / "agent.py").write_text(a, encoding="utf-8"); print("[OK] agent.py записан")
    else:
        FAILS.append("compile"); print("[FAIL] компиляция, не записан")
else:
    print("[WARN] agent.py НЕ записан из-за FAIL")

# --- D: дефолт окна 32768 везде, где он прописан ---
s = (AG / "settings.py").read_text(encoding="utf-8")
s2, n1 = re.subn(r'("num_ctx"\s*,\s*"[^"]*"\s*,\s*"int"\s*,\s*)8192', r"\g<1>32768", s)
s2, n2 = re.subn(r'"num_ctx"\s*:\s*\(\s*1024\s*,\s*32768\s*,\s*1024\s*\)', '"num_ctx": (1024, 65536, 1024)', s2)
if n1 or n2:
    if py_ok(s2, "settings.py"):
        (AG / "settings.py").write_text(s2, encoding="utf-8")
        print("[OK] D: settings.py дефолт %d, диапазон до 65536 (%d+%d замен)" % (32768, n1, n2))
    else:
        FAILS.append("D"); print("[FAIL] D: settings.py не компилируется")
else:
    SKIPS.append("D-registry"); print("[SKIP] D: строки регистра не узнаны, ставлю только config")
cp = AG / "data" / "config.json"
try:
    d = json.loads(cp.read_text(encoding="utf-8"))
    d["num_ctx"] = 32768
    cp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[OK] D: config.json num_ctx=32768")
except Exception as e:
    FAILS.append("D-cfg"); print("[FAIL] D: config.json: %s" % e)

print("\n=== CHECK ===")
ax = (AG / "agent.py").read_text(encoding="utf-8")
print("A:", "_SYS_CACHE.clear()" in ax)
print("B:", ax.count('"num_ctx": int(settings.get("num_ctx")'))
print("C:", '"think": _thk' in ax)
print("cfg:", json.loads(cp.read_text(encoding="utf-8")).get("num_ctx"))
print()
if FAILS: print("НЕ ПРИМЕНЕНО: " + "; ".join(FAILS))
else: print("ГОТОВО: .\\AI_RESTART.bat + Ctrl+F5")
if SKIPS: print("ПРОПУЩЕНО: " + "; ".join(SKIPS))