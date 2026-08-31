# -*- coding: utf-8 -*-
import io, re
p = r"D:\AI\tools\agent\creo_tools.py"
s = io.open(p, encoding="utf-8").read()
pat = re.compile(r"    seen, names = set\(\), \[\].*?    names = names\[:limit\]", re.S)
new = '''    seen, names = set(), []
    _mre = re.compile(r"\\.(prt|asm)(\\.\\d+)?$", re.I)
    lst = _flex_list((creo_call("creo", "list_files", {"filename": "*"}, 20) or {}).get("data"))
    if not lst:
        lst = _flex_list((creo_call("creo", "list_files", {"filename": "."}, 20) or {}).get("data"))
    for x in lst:
        s2 = str(x)
        if not _mre.search(s2):
            continue
        base = _mre.sub("", s2)
        if base not in seen:
            seen.add(base); names.append((base, s2))
    names = names[:limit]'''
if pat.search(s):
    s = pat.sub(lambda m: new, s, count=1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("[+] аудит: полный список + свой фильтр по расширению (маски и версии учтены)")
else:
    print("[x] блок аудита не найден")