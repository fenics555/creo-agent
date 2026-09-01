# -*- coding: utf-8 -*-
import io, re

# 1) find_tools: синонимы в обе стороны + регистр кириллицы + поиск по папкам
p = r"D:\AI\tools\agent\find_tools.py"
s = io.open(p, encoding="utf-8").read()
NEW_HEAD = '''SYNONYMS = {"турновер": ["переворот", "turnover"], "turnover": ["переворот", "турновер"],
    "ворошитель": ["переворот"], "переворот": ["турновер", "turnover"],
    "держатель": ["держател"]}

def _tokens(q):
    toks = [t.lower() for t in re.findall(r"[A-Za-zА-Яа-я0-9][A-Za-zА-Яа-я0-9.-]{2,}", q or "") if len(t) >= 3]
    out = []
    for t in toks:
        out.append(t)
        for key, syns in SYNONYMS.items():
            if key in t or t in key:
                out += syns
    return list(dict.fromkeys(out))

def _query(q, ext):
    toks = _tokens(q)
    conds, args = [], []
    if toks:
        per = []
        for t in toks:
            for v in (t, t.capitalize(), t.upper()):
                per.append("(name LIKE ? OR path LIKE ?)")
                args += ["%" + v + "%", "%" + v + "%"]
        conds.append("(" + " OR ".join(per) + ")")
    if ext:
        conds.append("ext = ?"); args.append(ext.lower().strip("."))
    return ((" WHERE " + " AND ".join(conds)) if conds else ""), args

'''
s2 = re.sub(r"SYNONYMS = .*?(?=\ndef _folder)", NEW_HEAD, s, count=1, flags=re.S)
if s2 == s:
    print("[x] find_tools: блок SYNONYMS не найден")
else:
    io.open(p, "w", encoding="utf-8").write(s2)
    print("[+] find_tools: синонимы в обе стороны + регистр кириллицы")

# 2) usage_tools: кнопка без параметров сама решает, полный или инкремент
p2 = r"D:\AI\tools\agent\usage_tools.py"
t = io.open(p2, encoding="utf-8").read()
old_anchor = re.search(r"([ \t]*)old_meta = dict\(c\.execute\(\"SELECT path, mtime FROM usage_meta\"\)\.fetchall\(\)\)", t)
if old_anchor and "if not full and not old_meta" not in t:
    ind = old_anchor.group(1)
    t = t.replace(old_anchor.group(0), old_anchor.group(0) + "\n" + ind + "if not full and not old_meta: full = True", 1)
    print("[+] usage_tools: авто-полный, если мета пуста")
t = re.sub(r'return "индекс строится в фоне[^"]*"',
           'return "индекс строится в фоне (авто: полный, если пусто; иначе инкремент); прогресс — usage_state; full=1 — принудительно (необязательно)"',
           t, count=1)
io.open(p2, "w", encoding="utf-8").write(t)
print("ГОТОВО: .\\AI_RESTART.bat")