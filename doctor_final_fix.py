# -*- coding: utf-8 -*-
import io

# 1) learn_tools: relations может прийти списком — приводим к строке
p = r"D:\AI\tools\agent\learn_tools.py"
s = io.open(p, encoding="utf-8").read()
old = 'if not rels or rels == "отношений нет" or rels.startswith("ошибка"):'
new = ('if isinstance(rels, list): rels = "\\n".join(str(x) for x in rels)\n    '
       'if not rels or rels == "отношений нет" or str(rels).startswith("ошибка"):')
if "isinstance(rels, list)" in s:
    print("[~] learn_tools уже фикс")
elif old in s:
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("[+] learn_tools: список relations -> строка")
else:
    print("[x] learn_tools: якорь не найден")

# 2) diagnostic_tools: save ДО rename (Creo не переименовывает несохранённую модель)
q = r"D:\AI\tools\agent\diagnostic_tools.py"
t = io.open(q, encoding="utf-8").read()
anchor = 'jrn = CT.creo_call("file", "rename", {"file": copy + ".prt", "new_name": copy + "_ren"}, 20)'
marker = "# save до rename (фикс General Error)"
if marker in t:
    print("[~] save-до-rename уже стоит")
elif anchor in t:
    t = t.replace(anchor, marker + '\n        CT.creo_call("file", "save", {"file": copy + ".prt"}, 20)\n        ' + anchor, 1)
    io.open(q, "w", encoding="utf-8").write(t)
    print("[+] creoson_full_test: save перед rename")
else:
    print("[x] diagnostic_tools: якорь rename не найден")
print("ТЕПЕРЬ: .\\AI_RESTART.bat, затем diag_learn и creoson_full_test")