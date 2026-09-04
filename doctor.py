# -*- coding: utf-8 -*-
# DOCTOR v15 — пакет правок по аудиту 09-04.
# Запускать ОДИН раз: python doctor.py ; старые doctor'ы НЕ перезапускать.

import re, json
from pathlib import Path

AG = Path(r"D:\AI\tools\agent")
FAILS = []

def fix(path, text, pattern, repl, what, flags=re.S | re.M):
    new, n = re.subn(pattern, repl, text, count=1, flags=flags)
    if not n:
        FAILS.append("%s: замена не найдена" % what)
        print("[FAIL] %s: замена не найдена" % what)
        return None
    try:
        compile(new, str(path), "exec")
    except SyntaxError as e:
        FAILS.append("%s: SyntaxError: %s" % (what, e))
        print("[FAIL] %s: SyntaxError: %s" % (what, e))
        return None
    path.write_text(new, encoding="utf-8")
    print("[OK] %s" % what)
    return new

# ---------- C1: set_val пишет config.json и возвращает True для любого ключа ----------
s = (AG / "settings.py").read_text(encoding="utf-8")
fix(AG / "settings.py", s, r"    return False\n",
    "    CONFIG_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding=\"utf-8\")\n    return True\n",
    "C1: set_val пишет config.json и True для любого ключа")

# ---------- C3: scanner.db -> WAL ----------
sc = (AG / "scanner.py").read_text(encoding="utf-8")
fix(AG / "scanner.py", sc, r"(def db\(\):\n\s*)return _sq\.connect\((.+)\)\s*$",
    r"\1c = _sq.connect(\2)\n    c.execute(\"PRAGMA journal_mode=WAL\")\n    return c",
    "C3: scanner.db() = WAL")

# ---------- W1a: web_save_rule под щит ----------
w = (AG / "web_tools.py").read_text(encoding="utf-8")
fix(AG / "web_tools.py", w,
    r'"approval"\s*:\s*False(\s*,\s*"fn"\s*:\s*tool_web_save_rule)',
    r'"approval": True\1',
    "W1a: web_save_rule approval=True")

# ---------- W1b: plm_mine под щит ----------
p = (AG / "plm_tools.py").read_text(encoding="utf-8")
fix(AG / "plm_tools.py", p,
    r'"approval"\s*:\s*False(\s*,\s*"fn"\s*:\s*tool_plm_mine)',
    r'"approval": True\1',
    "W1b: plm_mine approval=True")

# ---------- C5: parallel-ветка не дублирует основной TOOL ----------
a = (AG / "agent.py").read_text(encoding="utf-8")
fix(AG / "agent.py", a,
    r"\n([ \t]*)(if len\(others\) > 1:)",
    r"\n\1others = [o for o in others if (o[0], json.dumps(o[1], sort_keys=True, ensure_ascii=False)) != (name, json.dumps(args, sort_keys=True, ensure_ascii=False))]\n\1\2",
    "C5: parallel не дублирует основной инструмент")

# ---------- config.json: боевая модель -> 32b ----------
cp = AG / "data" / "config.json"
try:
    d = json.loads(cp.read_text(encoding="utf-8"))
    d["llm_model"] = "qwen2.5-coder:32b-instruct-q4_K_M"
    cp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[OK] config: llm_model -> qwen2.5-coder:32b-instruct-q4_K_M")
except Exception as e:
    FAILS.append("config.json: %s" % e)
    print("[FAIL] config.json: %s" % e)

# ---------- CHECK ----------
print("=== CHECK ===")
sx = (AG / "settings.py").read_text(encoding="utf-8")
print("settings пишет:", "CONFIG_FILE.write_text" in sx)
scx = (AG / "scanner.py").read_text(encoding="utf-8")
print("scanner WAL:", "journal_mode" in scx)
wx = (AG / "web_tools.py").read_text(encoding="utf-8")
print("web_save_rule:", "approval\": True" in wx.replace(" ", ""))
px = (AG / "plm_tools.py").read_text(encoding="utf-8")
print("plm_mine:", "approval\": True" in px.replace(" ", ""))
ax = (AG / "agent.py").read_text(encoding="utf-8")
print("agent parallel-fix:", "others = [o for o in others" in ax)
cfg = json.loads(cp.read_text(encoding="utf-8"))
print("config.llm_model:", cfg.get("llm_model"))

print()
if FAILS:
    print("НЕ ПРИМЕНЕНЫ: " + "; ".join(FAILS))
    print("Правки с FAIL не записаны. Остальные применены. Проверь вывод.")
else:
    print("ГОТОВО: .\\AI_RESTART.bat + Ctrl+F5 в браузере")