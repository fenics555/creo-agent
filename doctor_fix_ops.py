# -*- coding: utf-8 -*-
import io
ct = r"D:\AI\tools\agent\creo_tools.py"
s = io.open(ct, encoding="utf-8").read()
old_kids = '''def _kids(n):
    if not isinstance(n, dict):
        return []
    return n.get("children") or n.get("components") or n.get("models") or n.get("paths") or n.get("submodels") or []'''
new_kids = '''def _kids(n):
    if not isinstance(n, dict):
        return []
    c = n.get("children")
    if isinstance(c, dict):
        c = c.get("children") or []
    return c or n.get("components") or n.get("models") or n.get("paths") or n.get("submodels") or []'''
if new_kids in s: print("[~] _kids уже ок")
elif old_kids in s:
    s = s.replace(old_kids, new_kids, 1); print("[+] _kids: вложенный dict (BOM/спека)")
else: print("[x] _kids якорь не найден")
io.open(ct, "w", encoding="utf-8").write(s)

op = r"D:\AI\tools\agent\creo_ops_tools.py"
t = io.open(op, encoding="utf-8").read()
lines = t.splitlines(True)
for i, ln in enumerate(lines):
    if "new_lines = [ln.strip() for ln in str(relations)" in ln:
        lines.insert(i, '    if isinstance(relations, list): relations = "\\n".join(str(x) for x in relations)\n')
        print("[+] set_relations: список -> строка")
        break
t = "".join(lines)
if 'old_text = d if isinstance(d, str) else (d or {}).get("relations")' in t:
    t = t.replace('old_text = d if isinstance(d, str) else (d or {}).get("relations") or " "',
                  'old_text = d if isinstance(d, str) else ((d or {}).get("relations") if isinstance(d, dict) else "") or ""', 1)
    print("[+] set_relations: dict-безопасный old_text")
lines = t.splitlines(True)
for i, ln in enumerate(lines):
    if "re.sub" in ln and '.pdf"' in ln and "pdf =" in ln:
        lines[i] = '    pdf = re.sub(r"\\.(asm|prt|drw)(\\.\\d+)?$", "", nm, flags=re.I) + ".pdf"\n'
        print("[+] print_pdf: срез .asm/.prt/.drw перед .pdf")
        break
io.open(op, "w", encoding="utf-8").write("".join(lines))
print("ГОТОВО: .\\AI_RESTART.bat")