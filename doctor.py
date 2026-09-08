# -*- coding: utf-8 -*-
# DOCTOR v26 — управляемая видимость: think_in_log (строки THINK в ходе работы)
# и show_steps (блок «ХОД РАБОТЫ» в ответах). Форма кортежей копируется с stream_tokens.
# ЗАПУСК ОДИН РАЗ: python doctor.py   ПОТОМ: .\AI_RESTART.bat + Ctrl+F5
import re
from pathlib import Path

AG = Path(r"D:\AI\tools\agent")
FAILS = []; SKIPS = []

def py_ok(t, n):
    try:
        compile(t, n, "exec"); return True
    except SyntaxError as e:
        print("[SYNTAX] %s: %s" % (n, e)); return False

# --- 1. settings.py: два новых bool-ключа по образу строки stream_tokens ---
s = (AG / "settings.py").read_text(encoding="utf-8")
if '"think_in_log"' in s:
    SKIPS.append("S"); print("[SKIP] settings: ключи уже есть")
else:
    m = re.search(r'^[ \t]*\([^\n]*"stream_tokens"[^\n]*$', s, re.M)
    if not m:
        FAILS.append("S anchor"); print("[FAIL] settings: строка stream_tokens не найдена")
    else:
        tpl = m.group(0)
        def mk(key, name, dflt):
            line = tpl.replace('"stream_tokens"', '"%s"' % key)
            line = re.sub(r'("%s",\s*")[^"]*(")' % key, r"\g<1>%s\g<2>" % name, line)
            line = re.sub(r',\s*[01]\s*\)\s*$', ', %d)' % dflt, line)
            return line
        add = mk("think_in_log", "Строки THINK в ходе работы", 0) + "\n" + \
              mk("show_steps", "Ход работы в ответах", 1)
        s = s[:m.end()] + "\n" + add + s[m.end():]
        if py_ok(s, "settings.py"):
            (AG / "settings.py").write_text(s, encoding="utf-8")
            print("[OK] settings: think_in_log (0) и show_steps (1) добавлены")
        else:
            FAILS.append("S compile"); print("[FAIL] settings: не компилируется, не записано")

# --- 2. agent.py: строки THINK в лог только по тумблеру или log_mode>=2 ---
a = (AG / "agent.py").read_text(encoding="utf-8")
if "think_in_log" in a:
    SKIPS.append("A"); print("[SKIP] agent: условие THINK-лога уже есть")
else:
    pat = re.compile(r'if think:\n([ \t]+)_log\("\[THINK\] %s" % think\[:400\]\)')
    if not pat.search(a):
        FAILS.append("A anchor"); print("[FAIL] agent: строка _log THINK не найдена")
    else:
        a = pat.sub(lambda m: 'if think and (int(settings.get("think_in_log") or 0) or int(settings.get("log_mode") or 1) >= 2):\n%s_log("[THINK] %%s" %% think[:400])' % m.group(1), a, count=1)
        print("[OK] agent: THINK-лог под тумблером + override log_mode>=2")

# --- 3. PAGE: копилка значений настроек + гейт блока ХОД РАБОТЫ ---
if "window.CFG" in a:
    SKIPS.append("P"); print("[SKIP] PAGE: гейт уже есть")
else:
    ok_p = True
    old_bs = "s.items.forEach(function(it){h+="
    new_bs = "s.items.forEach(function(it){(window.CFG=window.CFG||{})[it.key]=it.value;h+="
    if old_bs in a: a = a.replace(old_bs, new_bs, 1)
    else: ok_p = False; FAILS.append("P1"); print("[FAIL] PAGE: якорь buildSettings не найден")
    old_r = "if(r.log&&r.log.length)h+="
    new_r = "if(r.log&&r.log.length&&(window.CFG||{}).show_steps!==0)h+="
    if old_r in a: a = a.replace(old_r, new_r, 1)
    else: ok_p = False; FAILS.append("P2"); print("[FAIL] PAGE: якорь render не найден")
    if ok_p: print("[OK] PAGE: show_steps управляет блоком ХОД РАБОТЫ")

if not FAILS:
    a2 = (AG / "agent.py").read_text(encoding="utf-8") if False else a
    if py_ok(a2, "agent.py"):
        (AG / "agent.py").write_text(a2, encoding="utf-8")
        print("[OK] agent.py записан")
    else:
        FAILS.append("A compile"); print("[FAIL] agent.py не компилируется, НЕ записан")
else:
    print("[WARN] agent.py НЕ записан из-за FAIL")

print("\n=== CHECK ===")
sx = (AG / "settings.py").read_text(encoding="utf-8")
ax = (AG / "agent.py").read_text(encoding="utf-8")
print("settings think_in_log:", '"think_in_log"' in sx)
print("settings show_steps:", '"show_steps"' in sx)
print("agent условие:", 'think_in_log' in ax)
print("page гейт:", 'window.CFG' in ax)
print()
if FAILS: print("НЕ ПРИМЕНЕНО: " + "; ".join(FAILS))
else: print("ГОТОВО: .\\AI_RESTART.bat + Ctrl+F5")
if SKIPS: print("ПРОПУЩЕНО: " + "; ".join(SKIPS))