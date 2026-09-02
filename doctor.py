# -*- coding: utf-8 -*-
import re, sys
from pathlib import Path
AG = Path(r"D:\AI\tools\agent")
sp = AG / "settings.py"                      # <-- исправлено: settings.py в agent/
s = sp.read_text(encoding="utf-8")

# 1) чиним битый Web-блок (9 элементов -> три нормальных кортежа)
pat = re.compile(r'[ \t]*\("Web",\s*\n\s*\("Web",\s*"web_jina_key".*?"Внешняя цель для diag_web\.",\s*True\),', re.S)
clean = ('    ("Web", "web_jina_key", "Ключ r.jina.ai", "str", "", "Если есть ключ — прокси оживает.", True),\n'
         '    ("Web", "web_render", "Рендер браузером (Playwright)", "bool", False, "Вкл: при сбое fetch — headless Chrome.", True),\n'
         '    ("Web", "web_test_url", "URL для diag_web", "str", "https://ya.ru", "Внешняя цель для diag_web.", True),')
s, n = pat.subn(clean, s, count=1)
print("[+] settings: битый Web-блок починен" if n else "[~] битый блок не найден")

# 2) дедупликация ключей (оставляем первое вхождение)
out, seen = [], set()
for ln in s.split("\n"):
    m = re.match(r'\s*\("[^"]+",\s*"([^"]+)",', ln)
    if m:
        if m.group(1) in seen: continue
        seen.add(m.group(1))
    out.append(ln)
s = "\n".join(out)
sp.write_text(s, encoding="utf-8")
print("[+] settings: дубли убраны, ключей:", len(seen))

# 3) проверка: все кортежи по 7
sys.path.insert(0, str(AG)); sys.path.insert(0, str(AG.parent))
try:
    import importlib, settings
    importlib.reload(settings)
    bad = [e for e in settings.REGISTRY if not (isinstance(e, tuple) and len(e) == 7)]
    print("REGISTRY: записей %d, битых: %s" % (len(settings.REGISTRY), bad or "нет"))
except Exception as e:
    print("[x] импорт settings:", e)
print("ГОТОВО: .\\AI_RESTART.bat")