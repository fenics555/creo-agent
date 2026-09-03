# -*- coding: utf-8 -*-
import re, ast, sys
from pathlib import Path
AG = Path(r"D:\AI\tools\agent"); sys.path.insert(0, str(AG))

for fn in ("agent.py", "scanner.py", "settings.py", "core.py"):
    try:
        ast.parse((AG / fn).read_text(encoding="utf-8"))
        print("[OK] %s: синтаксис" % fn)
    except SyntaxError as e:
        print("[CRITICAL] %s: SyntaxError стр %d: %s" % (fn, e.lineno, e.msg))

a = (AG / "agent.py").read_text(encoding="utf-8")
m = re.search(r"def _log\(line\):.*", a)
print("\n_log:", m.group(0).strip() if m else "нет")
if m and "_log(line);" in m.group(0):
    a = a.replace(m.group(0), "def _log(line): steps_log.append(line); LIVE.setdefault(client, []).append(line)")
    print("[FIX] _log: рекурсия убрана")
    ch = True
else: ch = False

print("concurrent-импорт:", [l.strip() for l in a.splitlines() if "concurrent" in l])
print("__main__:", [l.strip() for l in a.splitlines() if "__main__" in l][:1])
print("дубли прямого вызова в ask:", a.count("name = q.strip()"))

import core
base = str(getattr(core, "BASE", ""))
print("\ncore.BASE =", base, "| совпадает с папкой агента:", base == str(AG))
if base != str(AG) and "cwd=str(core.BASE)" in a:
    a = a.replace("cwd=str(core.BASE)", 'cwd=r"D:\\AI\\tools\\agent"')
    print("[FIX] /rescan,/scan: cwd -> папка агента"); ch = True
if ch: (AG / "agent.py").write_text(a, encoding="utf-8")

s = (AG / "scanner.py").read_text(encoding="utf-8")
for fn in ("def _pats", "def is_excluded", "def db", "def read_roots"):
    print("%s(: определений %d (работает последняя)" % (fn, s.count(fn + "(")))
print("\nJS-опечатки с пробелами:", [w for w in ("creo_au dit", "copy_mode l", "wi zard", "d ocument") if w in a] or "нет")
print("\nГОТОВО: .\\AI_RESTART.bat, затем спроси в чате что-нибудь с шагом инструмента (например «какая модель открыта») — если ответ приходит без «ошибки», рекурсия мертва")