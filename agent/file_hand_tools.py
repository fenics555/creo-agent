# file_hand_tools.py — руки дома: список, запись, правка файлов с согласованием и предохранителем
# -*- coding: utf-8 -*-
import os, shutil, subprocess, datetime, sys, fnmatch
from pathlib import Path
import core
from core import log, REPO, BASE

AG = os.path.dirname(os.path.abspath(__file__))
ALLOW = (r"D:\\AI\\repo", AG)
DENY_FILES = ("users.py", "users.json", "agent.pid")
DENY_DIRS = ("data\\backup", ".git")

def _ok(p):
    p = os.path.abspath(p)
    if not p.startswith(ALLOW): return False, "путь вне разрешённых корней"
    for d in DENY_DIRS:
        if ("\\" + d + "\\") in (p + "\\"): return False, "запрещённый каталог " + d
    if os.path.basename(p) in DENY_FILES: return False, "запрещённый файл " + os.path.basename(p)
    return True, p

def _bak(p):
    b = os.path.join(AG, "data", "backup", "pre_fs_%s_%s" % (
        datetime.datetime.now().strftime("%y%m%d_%H%M%S"), os.path.basename(p)))
    shutil.copy2(p, b); return b

def _compile(p):
    if not p.lower().endswith(".py"): return True, ""
    r = subprocess.run([sys.executable, "-m", "py_compile", p], capture_output=True, text=True)
    return r.returncode == 0, (r.stderr or "")[:500]

def tool_fs_list(path=AG, mask="*"):
    ok, p = _ok(path)
    if not ok: return {"error": p}
    if not os.path.isdir(p): return {"error": "не каталог"}
    out = []
    for f in sorted(os.listdir(p)):
        if fnmatch.fnmatch(f, mask):
            fp = os.path.join(p, f)
            out.append({"name": f, "dir": os.path.isdir(fp),
                        "size": os.path.getsize(fp) if os.path.isfile(fp) else 0})
    return {"path": p, "items": out[:200]}

def tool_fs_write(path, text):
    ok, p = _ok(path)
    if not ok: return {"error": p}
    d = os.path.dirname(p)
    if d and not os.path.isdir(d): os.makedirs(d, exist_ok=True)
    bak = _bak(p) if os.path.exists(p) else None
    open(p, "w", encoding="utf-8", newline="").write(text)
    cok, err = _compile(p)
    if not cok:
        if bak: shutil.copy2(bak, p)
        return {"error": "компиляция провалена, откат: " + err}
    return {"ok": True, "path": p, "backup": bak, "bytes": len(text)}

def tool_fs_edit(path, old, new):
    ok, p = _ok(path)
    if not ok: return {"error": p}
    if not os.path.exists(p): return {"error": "нет файла"}
    
    s = None
    for enc in ['utf-8', 'cp1251']:
        try:
            with open(p, 'r', encoding=enc) as f:
                s = f.read()
            if s and '\\ufffd' not in s:
                break
        except:
            continue
    
    if s is None:
        s = open(p, 'r', encoding='utf-8', errors='replace').read()

    n = s.count(old)
    if n != 1: return {"error": "old встретился %d раз, нужен ровно 1" % n}
    bak = _bak(p)
    open(p, "w", encoding="utf-8", newline="").write(s.replace(old, new, 1))
    cok, err = _compile(p)
    if not cok:
        shutil.copy2(bak, p)
        return {"error": "компиляция провалена, откат: " + err}
    return {"ok": True, "path": p, "backup": bak}

fs_edit = tool_fs_edit
fs_write = tool_fs_write
fs_list = tool_fs_list

TOOLS = [
    {"name": "fs_list", "desc": "Список файлов каталога с маской (только чтение)",
     "params": {"path": "каталог", "mask": "маска"}, "approval": False, "fn": tool_fs_list},
    {"name": "fs_write", "desc": "Запись файла целиком; бекап до записи, для .py компиляционный предохранитель с откатом",
     "params": {"path": "файл", "text": "содержимое"}, "approval": True, "fn": tool_fs_write},
    {"name": "fs_edit", "desc": "Точечная правка: old обязан встретиться ровно один раз; бекап и предохранитель",
     "params": {"path": "файл", "old": "точный фрагмент", "new": "замена"}, "approval": True, "fn": tool_fs_edit},
]

# file_hand_tools.py — руки дома: список, запись, правка файлов с согласованием и предохранителем
# -*- coding: utf-8 -*-
import os, shutil, subprocess, datetime, sys, fnmatch
from pathlib import Path
import core
from core import log, REPO, BASE

AG = os.path.dirname(os.path.abspath(__file__))
ALLOW = (r"D:\AI\repo", AG)
DENY_FILES = ("users.py", "users.json", "agent.pid")
DENY_DIRS = ("data\backup", ".git")

def _ok(p):
    p = os.path.abspath(p)
    if not p.startswith(ALLOW): return False, "путь вне разрешённых корней"
    for d in DENY_DIRS:
        if ("\\" + d + "\\") in (p + "\\"): return False, "запрещённый каталог " + d
    if os.path.basename(p) in DENY_FILES: return False, "запрещённый файл " + os.path.basename(p)
    return True, p

def _bak(p):
    b = os.path.join(AG, "data", "backup", "pre_fs_%s_%s" % (
        datetime.datetime.now().strftime("%y%m%d_%H%M%S"), os.path.basename(p)))
    shutil.copy2(p, b); return b

def _compile(p):
    if not p.lower().endswith(".py"): return True, ""
    r = subprocess.run([sys.executable, "-m", "py_compile", p], capture_output=True, text=True)
    return r.returncode == 0, (r.stderr or "")[:500]

def tool_fs_list(path=AG, mask="*"):
    ok, p = _ok(path)
    if not ok: return {"error": p}
    if not os.path.isdir(p): return {"error": "не каталог"}
    out = []
    for f in sorted(os.listdir(p)):
        if fnmatch.fnmatch(f, mask):
            fp = os.path.join(p, f)
            out.append({"name": f, "dir": os.path.isdir(fp),
                        "size": os.path.getsize(fp) if os.path.isfile(fp) else 0})
    return {"path": p, "items": out[:200]}

def tool_fs_write(path, text):
    ok, p = _ok(path)
    if not ok: return {"error": p}
    d = os.path.dirname(p)
    if d and not os.path.isdir(d): os.makedirs(d, exist_ok=True)
    bak = _bak(p) if os.path.exists(p) else None
    open(p, "w", encoding="utf-8", newline="").write(text)
    cok, err = _compile(p)
    if not cok:
        if bak: shutil.copy2(bak, p)
        return {"error": "компиляция провалена, откат: " + err}
    return {"ok": True, "path": p, "backup": bak, "bytes": len(text)}

def tool_fs_edit(path, old, new):
    ok, p = _ok(path)
    if not ok: return {"error": p}
    if not os.path.exists(p): return {"error": "нет файла"}
    
    s = None
    for enc in ['utf-8', 'cp1251']:
        try:
            with open(p, 'r', encoding=enc) as f:
                s = f.read()
            if s and '\ufffd' not in s:
                break
        except:
            continue
    
    if s is None:
        s = open(p, 'r', encoding='utf-8', errors='replace').read()

    n = s.count(old)
    if n != 1: return {"error": "old встретился %d раз, нужен ровно 1" % n}
    bak = _bak(p)
    open(p, "w", encoding="utf-8", newline="").write(s.replace(old, new, 1))
    cok, err = _compile(p)
    if not cok:
        shutil.copy2(bak, p)
        return {"error": "компиляция провалена, откат: " + err}
    return {"ok": True, "path": p, "backup": bak}

TOOLS = [
    {"name": "fs_list", "desc": "Список файлов каталога с маской (только чтение)",
     "params": {"path": "каталог", "mask": "маска"}, "approval": False, "fn": tool_fs_list},
    {"name": "fs_write", "desc": "Запись файла целиком; бекап до записи, для .py компиляционный предохранитель с откатом",
     "params": {"path": "файл", "text": "содержимое"}, "approval": True, "fn": tool_fs_write},
    {"name": "fs_edit", "desc": "Точечная правка: old обязан встретиться ровно один раз; бекап и предохранитель",
     "params": {"path": "файл", "old": "точный фрагмент", "new": "замена"}, "approval": True, "fn": tool_fs_edit},
]
