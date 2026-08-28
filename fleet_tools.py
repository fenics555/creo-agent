# -*- coding: utf-8 -*-
# doctor7: запрет кеша страницы. Запуск: python doctor7.py
from pathlib import Path
ap = Path(r"D:\AI\tools\agent\agent.py")
s = ap.read_text(encoding="utf-8")
old = 'self.send_header("Content-Type", "text/html; charset=utf-8")'
new = ('self.send_header("Content-Type", "text/html; charset=utf-8")\n'
       '            self.send_header("Cache-Control", "no-store")')
if "no-store" in s:
    print("уже стоит")
elif old in s:
    ap.write_text(s.replace(old, new, 1), encoding="utf-8")
    print("ok: no-store добавлен")
else:
    print("якорь не найден")