# -*- coding: utf-8 -*-
# DOCTOR v24 — три фикса настроек агента:
#   A) /setcfg сбрасывает кэш системного промта (think_mode и пр. живут без рестарта)
#   B) num_ctx реально уходит в options запроса к Ollama
#   C) параметр think в /api/chat для думающих семейств (qwen3/deepseek) по think_mode
# ЗАПУСКАТЬ ОДИН РАЗ: python doctor.py   ПОТОМ: .\AI_RESTART.bat + Ctrl+F5
from pathlib import Path

AG = Path(r"D:\AI\tools\agent")
FAILS = []; SKIPS = []

def py_ok(t, n):
    try:
        compile(t, n, "exec"); return True
    except SyntaxError as e:
        print("[SYNTAX] %s: %s" % (n, e)); return False

a = (AG / "agent.py").read_text(encoding="utf-8")

# --- FIX A: инвалидация _SYS_CACHE в /setcfg ---
old_a = 'settings.set_val(b.get("key"), b.get("value")); self._j({"ok": True})'
new_a = 'settings.set_val(b.get("key"), b.get("value")); _SYS_CACHE.clear(); self._j({"ok": True})'
if "_SYS_CACHE.clear()" in a:
    SKIPS.append("A"); print("[SKIP] A: кэш уже сбрасывается")
elif old_a in a:
    a = a.replace(old_a, new_a, 1); print("[OK] A: _SYS_CACHE.clear() в /setcfg")
else:
    FAILS.append("A anchor"); print("[FAIL] A: якорь /setcfg не найден")

# --- FIX B: num_ctx в options обеих ветвей beh() ---
old_b1 = '"num_predict": int(settings.get("num_predict") or 1536)}, steps)'
new_b1 = '"num_predict": int(settings.get("num_predict") or 1536), "num_ctx": int(settings.get("num_ctx") or 8192)}, steps)'
old_b2 = '"num_predict": int(settings.get("num_predict") or 1024)}, steps)'
new_b2 = '"num_predict": int(settings.get("num_predict") or 1024), "num_ctx": int(settings.get("num_ctx") or 8192)}, steps)'
if a.count('"num_ctx": int(settings.get("num_ctx")') >= 2:
    SKIPS.append("B"); print("[SKIP] B: num_ctx уже в options")
else:
    ok_b = True
    if old_b1 in a: a = a.replace(old_b1, new_b1, 1)
    else: ok_b = False; FAILS.append("B1 anchor"); print("[FAIL] B: якорь 1536 не найден")
    if old_b2 in a: a = a.replace(old_b2, new_b2, 1)
    else: ok_b = False; FAILS.append("B2 anchor"); print("[FAIL] B: якорь 1024 не найден")
    if ok_b: print("[OK] B: num_ctx в обеих ветвях beh()")

# --- FIX C: параметр think в запросе /api/chat ---
anc_c = 'if invalid_cnt: use_opts = dict(use_opts, temperature=0)'
old_c = '"stream": False, "options": use_opts, "messages": messages}, t=600)'
new_c = '"stream": False, "think": _thk, "options": use_opts, "messages": messages}, t=600)'
thk_line = '_thk = int(settings.get("think_mode") or 0) > 0 and (settings.model_for("chat") or "").startswith(("qwen3", "deepseek"))'
if '"think": _thk' in a:
    SKIPS.append("C"); print("[SKIP] C: think уже в запросе")
elif anc_c in a and old_c in a:
    i = a.index(anc_c)
    ls = a.rfind("\n", 0, i) + 1
    ind = a[ls:i]
    a = a.replace(anc_c, anc_c + "\n" + ind + thk_line, 1)
    a = a.replace(old_c, new_c, 1)
    print("[OK] C: параметр think в запросе (qwen3/deepseek, по think_mode)")
else:
    FAILS.append("C anchor"); print("[FAIL] C: якоря run_loop не найдены")

# --- запись с гейтом компиляции ---
if not FAILS:
    if py_ok(a, "agent.py"):
        (AG / "agent.py").write_text(a, encoding="utf-8")
        print("[OK] agent.py записан")
    else:
        FAILS.append("compile"); print("[FAIL] компиляция, файл не записан")
else:
    print("[WARN] из-за FAIL файл НЕ записан")

print("\n=== CHECK ===")
ax = (AG / "agent.py").read_text(encoding="utf-8")
print("A: _SYS_CACHE.clear() в setcfg:", "_SYS_CACHE.clear()" in ax)
print("B: вхождений num_ctx в options:", ax.count('"num_ctx": int(settings.get("num_ctx")'))
print("C: think в запросе:", '"think": _thk' in ax)
print()
if FAILS: print("НЕ ПРИМЕНЕНО: " + "; ".join(FAILS))
else: print("ГОТОВО: .\\AI_RESTART.bat + Ctrl+F5")
if SKIPS: print("ПРОПУЩЕНО: " + "; ".join(SKIPS))