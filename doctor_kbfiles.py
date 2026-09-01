# -*- coding: utf-8 -*-
import io, re
from pathlib import Path
BASE = Path(r"D:\AI\tools\agent")

ROOTS = """# одна папка в строке
D:\\PTC\\CREO12\\Creo 12.4.2.0\\creo_help_pma\\russian
D:\\AI\\repo
Z:\\PTC\\Work
Z:\\PTC\\CREO-START
"""
EXCL = """# Исключения для индексации и скана
# Строка = шаблон. * - любой путь/имя.
# Папки (заканчиваются на \\ или /)
.git\\
__pycache__\\
node_modules\\
venv\\
.venv\\
backup\\
old\\
temp\\
tmp\\
cache\\
.idea\\
.vscode\\
Z:\\PTC\\Work\\000_03 401-LIT Литейное производство\\000_5 401-LIT-MO Модельная оснастка для литья\\000_10 СТОРОННИЕ РАЗРАБОТКИ\\
Z:\\PTC\\Work\\УЧЕБА\\
# Файлы
Thumbs.db
desktop.ini
*.tmp
*.bak
*~
*.log
*.sqlite
*.db
*.exe
*.dll
*.so
*.o
*.obj
*.pyc
.DS_Store
"""

for name, txt in (("kb_roots.txt", ROOTS), ("kb_exclude.txt", EXCL)):
    f = BASE / name
    if not f.exists():
        f.write_text(txt, encoding="utf-8")
        print("[+] создан %s" % name)
    else:
        print("[~] %s уже есть" % name)

sp = BASE / "scanner.py"
s = sp.read_text(encoding="utf-8")

NEW_ROOTS = '''def read_roots():
    from pathlib import Path as _P
    import core as _c
    out = []
    for base in (_c.BASE, _c.REPO):
        f = _P(base) / "kb_roots.txt"
        if f.exists():
            for ln in f.read_text(encoding="utf-8", errors="ignore").splitlines():
                ln = ln.strip()
                if ln and not ln.startswith("#"):
                    out.append(ln)
            break
    return out or [str(_c.REPO)]
'''
NEW_PATS = '''def _pats():
    from pathlib import Path as _P
    import core as _c
    pats = []
    for base in (_c.BASE, _c.REPO):
        f = _P(base) / "kb_exclude.txt"
        if f.exists():
            for ln in f.read_text(encoding="utf-8", errors="ignore").splitlines():
                ln = ln.strip()
                if ln and not ln.startswith("#"):
                    pats.append(ln)
            break
    return pats
'''

def repl(src, fname, body):
    i = src.find("def %s(" % fname)
    if i < 0:
        print("[x] не найдена %s" % fname); return src
    j = src.find("\ndef ", i + 5)
    if j < 0: j = len(src)
    return src[:i] + body + src[j:]

s2 = repl(s, "read_roots", NEW_ROOTS)
s2 = repl(s2, "_pats", NEW_PATS)
if s2 != s:
    sp.write_text(s2, encoding="utf-8")
    print("[+] scanner.py: корни и исключения читаются из kb_roots.txt / kb_exclude.txt")
else:
    print("[~] scanner.py уже читает файлы (или функции не найдены — провери вручную)")
print("ГОТОВО: .\\AI_RESTART.bat, затем scan_run / index_run")