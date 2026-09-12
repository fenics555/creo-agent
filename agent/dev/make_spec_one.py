# -*- coding: utf-8 -*-
r"""Собирает ОДИН блок spec_tools.py из excel_import.py + excel_export.py (Давыдовка) + связка с агентом.
Запуск: python make_spec_one.py. Обновились файлы Давыдовки — просто перезапустить."""
import io, os, re

BASE = r"D:\AI\tools\agent"
HEAD = '''# -*- coding: utf-8 -*-
r"""SPEC (единый блок): создание/чтение XLSX (Давыдовка) + связка с агентом:
секции по параметру ТИП, состав через CREOSON. Собран make_spec_one.py —
руками не править, править источники и перезапускать сборку."""
from __future__ import annotations
'''

GLUE = '''
import os
import creo_tools as CT

def _sec_by_type(v):
    t = str(v or "").strip().upper()
    return {"ДОКУМЕНТ": "Документация", "КОМПЛЕКС": "Комплексы", "СБОРКА": "Сборочные единицы",
            "ДЕТАЛЬ": "Детали", "СТАНДАРТНОЕ": "Стандартные изделия", "ПРОЧЕЕ": "Прочие изделия",
            "МАТЕРИАЛ": "Материалы", "КОМПЛЕКТ": "Комплекты"}.get(t, "")

def _pval(plist, names):
    want = [n.upper() for n in names]
    for p in plist:
        if str(p.get("name", "")).upper() in want:
            return p.get("value")
    return None

def _params_of(f):
    j = CT.creo_call("parameter", "list", {"file": f}, 20)
    if not CT.ok(j):
        return []
    return (j.get("data") or {}).get("param_list") or []

def tool_spec_create_active(**kw):
    act = CT.tool_get_active()
    if not act:
        return "нет активной модели в Creo"
    wd = CT.tool_pwd()
    base = re.sub(r"\\.(asm|prt|drw)(\\.\\d+)?$", "", act, flags=re.I)
    ap = _params_of(act)
    designation = str(_pval(ap, ["ОБОЗНАЧЕНИЕ", "DESIGNATION"]) or base)
    j = CT.creo_call("bom", "get_paths", {"file": act, "paths": False, "top_level": False, "exclude_inactive": True}, 30)
    root = (j.get("data") or {}) if CT.ok(j) else {}
    seen, comps, stack = set(), [], list(root.get("children") or [])
    while stack:
        node = stack.pop()
        if not isinstance(node, dict):
            continue
        f = str(node.get("file") or "")
        if f and f not in seen:
            seen.add(f); comps.append(f)
        stack.extend(node.get("children") or [])
    if not comps:
        return "сборка пуста или BOM не прочитался"
    rows = []
    for f in comps:
        pl = _params_of(f)
        sec = _sec_by_type(_pval(pl, ["ТИП"])) or ("Сборочные единицы" if f.lower().endswith(".asm") else "Детали")
        rows.append({"section": sec,
                     "format": str(_pval(pl, ["ФОРМАТ", "FORMAT"]) or ""),
                     "zone": str(_pval(pl, ["ЗОНА", "ZONE"]) or ""),
                     "position": str(_pval(pl, ["ПОЗИЦИЯ", "POSITION"]) or ""),
                     "designation": "" if sec == "Стандартные изделия" else str(_pval(pl, ["ОБОЗНАЧЕНИЕ", "DESIGNATION"]) or re.sub(r"\\.(asm|prt|drw)(\\.\\d+)?$", "", f, flags=re.I)),
                     "name": str(_pval(pl, ["НАИМЕНОВАНИЕ", "NAME"]) or ""),
                     "quantity": "1",
                     "note": str(_pval(pl, ["ПРИМЕЧАНИЕ", "NOTE"]) or "")})
    canon = ["Документация", "Комплексы", "Сборочные единицы", "Детали", "Стандартные изделия", "Прочие изделия", "Материалы", "Комплекты"]
    used = [{"name": c} for c in canon if any(r["section"] == c for r in rows)]
    try:
        out, n_rows, n_img = create_xlsx(wd, designation, used, rows, [], act)
    except ValueError as e:
        return "XLSX не создан: %s" % e
    return "спецификация записана: %s (строк: %d, картинок: %d)" % (out, n_rows, n_img)

def tool_spec_read(path="", **kw):
    p = (path or "").strip().strip('"')
    if not p or not os.path.isfile(p):
        return "укажи существующий путь к XLSX"
    try:
        with open(p, "rb") as f:
            sections, rows = read_specification_xlsx(f.read())
    except ValueError as e:
        return "ошибка XLSX: %s" % e
    out = ["разделы: " + ", ".join(sections), "строк: %d" % len(rows)]
    out += ["- [%s] %s | %s | кол %s" % (r.get("section"), r.get("designation"), r.get("name"), r.get("quantity")) for r in rows[:25]]
    if len(rows) > 25:
        out.append("…и ещё %d" % (len(rows) - 25))
    return "\\n".join(out)

TOOLS = [
    {"name": "spec_create_active", "desc": "ГОСТ-спецификация (XLSX) в папку сборки из живого Creo: разделы по ТИП, состав по BOM", "params": {}, "approval": True, "fn": tool_spec_create_active},
    {"name": "spec_read", "desc": "Прочитать XLSX-спецификацию: разделы и строки", "params": {"path": "путь к xlsx"}, "approval": False, "fn": tool_spec_read},
]
'''

def strip_future(t):
    return re.sub(r"(?m)^\s*from __future__ import annotations\s*$", "", t)

def main():
    parts = [HEAD]
    for fn in ("excel_import.py", "excel_export.py"):
        p = os.path.join(BASE, fn)
        if not os.path.isfile(p):
            print("[x] не найден %s — положи рядом" % fn); return
        parts.append(strip_future(io.open(p, encoding="utf-8").read()))
    parts.append(GLUE)
    text = "".join(parts)
    io.open(os.path.join(BASE, "spec_tools.py"), "w", encoding="utf-8").write(text)
    print("[+] spec_tools.py собран: %d строк, один блок" % len(text.splitlines()))

if __name__ == "__main__":
    main()