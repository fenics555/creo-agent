# -*- coding: utf-8 -*-
# DOCTOR v25 — видимые мысли: T1 читает message.thinking в run_loop,
# T2 копит thinking в стриминге, T3 выключает нативные размышления при think_mode=0.
# ЗАПУСКАТЬ ОДИН РАЗ. После: .\AI_RESTART.bat + Ctrl+F5
from pathlib import Path
AG = Path(r"D:\AI\tools\agent")
FAILS = []; SKIPS = []

def py_ok(t, n):
    try:
        compile(t, n, "exec"); return True
    except SyntaxError as e:
        print("[SYNTAX] %s: %s" % (n, e)); return False

def save(p, t):
    if py_ok(t, str(p)):
        p.write_text(t, encoding="utf-8"); return True
    FAILS.append(p.name); return False

a = (AG / "agent.py").read_text(encoding="utf-8")

# T1: дочитывать нативные мысли из message.thinking
anc1 = "kind, payload, args, think = parse_model(raw)"
if "think = think or" in a:
    SKIPS.append("T1"); print("[SKIP] T1 уже есть")
elif anc1 in a:
    a = a.replace(anc1, anc1 + '\n        think = think or (((r.get("message") or {}).get("thinking") or "").strip())', 1)
    print("[OK] T1: thinking из message.thinking")
else:
    FAILS.append("T1 anchor"); print("[FAIL] T1: якорь не найден")

# T2: стриминг тоже копит thinking
if "thparts" in a:
    SKIPS.append("T2"); print("[SKIP] T2 уже есть")
else:
    ok = True
    a2 = 'parts = []; state = {"buf": "", "mode": None}; lastj = {}'
    if a2 in a:
        a = a.replace(a2, a2 + "\n    thparts = []", 1)
    else:
        ok = False; FAILS.append("T2a"); print("[FAIL] T2: якорь parts")
    b2 = 't = (j.get("message") or {}).get("content") or ""'
    if ok and b2 in a:
        a = a.replace(b2, b2 + '\n                tth = (j.get("message") or {}).get("thinking") or ""\n                if tth: thparts.append(tth)', 1)
    else:
        ok = False; FAILS.append("T2b"); print("[FAIL] T2: якорь content")
    c2 = 'r = {"message": {"content": "".join(parts)}}'
    if ok and c2 in a:
        a = a.replace(c2, 'r = {"message": {"content": "".join(parts), "thinking": "".join(thparts)}}', 1)
    else:
        ok = False; FAILS.append("T2c"); print("[FAIL] T2: якорь return")
    if ok: print("[OK] T2: стриминг копит thinking")

# T3: при think_mode=0 просим Ollama не думать (экономия тех самых скрытых токенов)
if "_post_think_off" in a:
    SKIPS.append("T3"); print("[SKIP] T3 уже есть")
elif "core.post = _stream_post" in a:
    a = a.replace("core.post = _stream_post", '''core.post = _stream_post
_post_before_think = core.post
def _post_think_off(path, payload, *ar, **kw):
    if path == "/api/chat" and isinstance(payload, dict):
        payload = dict(payload)
        if int(settings.get("think_mode") or 0) == 0:
            payload["think"] = False
    return _post_before_think(path, payload, *ar, **kw)
core.post = _post_think_off''', 1)
    print("[OK] T3: think_mode=0 выключает нативные размышления")
else:
    FAILS.append("T3 anchor"); print("[FAIL] T3: якорь не найден")

if not FAILS:
    if save(AG / "agent.py", a):
        print("[OK] agent.py записан")

print("\n=== CHECK ===")
ax = (AG / "agent.py").read_text(encoding="utf-8")
print("T1:", "think = think or" in ax)
print("T2:", "thparts" in ax)
print("T3:", "_post_think_off" in ax)
print()
if FAILS: print("НЕ ПРИМЕНЕНО: " + "; ".join(FAILS))
else: print("ГОТОВО: .\\AI_RESTART.bat + Ctrl+F5")
if SKIPS: print("ПРОПУЩЕНО: " + "; ".join(SKIPS))