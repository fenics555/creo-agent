# -*- coding: utf-8 -*-
import io
from pathlib import Path as _P
fp = _P(r"D:\AI\tools\agent\find_tools.py")
s = fp.read_text(encoding="utf-8")
if "from pathlib import Path" not in s:
    s = s.replace("import core\n", "import core\nfrom pathlib import Path\n", 1)

NEW = r'''_FAMRUN = re.compile(rb"[A-Za-z0-9_\-]{3,}")

def _fam_instances(dirp, gen):
    gl = gen.lower()
    res = []
    for ip in dirp.iterdir():
        if not ip.is_file(): continue
        low = ip.name.lower()
        if not re.search(r"\.(prt|xpr)(\.\d+)?$", low): continue
        base = re.sub(r"\.(prt|xpr)(\.\d+)?$", "", low)
        if base == gl: continue
        if ("<%s>" % gl) in low or base.startswith(gl + "-") or base.startswith(gl + "_"):
            res.append(ip)
    return sorted(res, key=lambda p: p.name)

def _fam_row(name, gen):
    base = re.sub(r"\.(prt|xpr)(\.\d+)?$", "", name, flags=re.I)
    base = re.sub(r"<%s>$" % re.escape(gen), "", base, flags=re.I)
    return base

def _fam_parse(gp):
    gen = re.sub(r"\.(prt|xpr)(\.\d+)?$", "", gp.name, flags=re.I)
    data = gp.read_bytes()
    strs = {m.group(0).decode().lower() for m in _FAMRUN.finditer(data)}
    rows, ghost = [], []
    for ip in _fam_instances(gp.parent, gen):
        row = _fam_row(ip.name, gen)
        (rows if row.lower() in strs else ghost).append(row)
    rows = sorted(set(rows)); ghost = sorted(set(ghost))
    nested = sorted({r for r in rows if _fam_instances(gp.parent, r)})
    missing = sorted(x for x in strs
                     if x != gen.lower() and not re.fullmatch(r"d\d+", x)
                     and x.startswith(gen.lower() + "-")
                     and not _fam_instances(gp.parent, x))
    return {"generic": gen, "rows": rows, "nested": nested, "missing": missing, "ghost": ghost}

def tool_family_parse(q="", **kw):
    q = (q or "").strip()
    if not q: return "укажи имя generic или путь к .prt"
    p = Path(q)
    if not p.exists():
        c = core.db()
        row = c.execute("SELECT path FROM models WHERE LOWER(name)=? AND ext IN ('prt','xpr')", (q.lower() + ".prt",)).fetchone() \
              or c.execute("SELECT path FROM models WHERE LOWER(name) LIKE ? AND ext IN ('prt','xpr') LIMIT 1", (q.lower() + "%",)).fetchone()
        c.close()
        if not row: return "не нашёл generic: %s" % q
        p = Path(row[0])
    r = _fam_parse(p)
    out = ["GENERIC %s: строк таблицы %d (вложенных %d)" % (r["generic"], len(r["rows"]), len(r["nested"]))]
    out += ["  - %s%s" % (x, "  <- вложенная таблица" if x in r["nested"] else "") for x in r["rows"][:40]]
    if len(r["rows"]) > 40: out.append("  …и ещё %d" % (len(r["rows"]) - 40))
    if r["nested"]: out.append("вложенные: %s" % ", ".join(r["nested"]))
    if r["missing"]: out.append("строки без файлов на диске: %s" % ", ".join(r["missing"][:10]))
    if r["ghost"]: out.append("файлы без строки в бинарнике: %s" % ", ".join(r["ghost"][:10]))
    return "\n".join(out)

if not any(t.get("name") == "family_parse" for t in TOOLS):
    TOOLS.append({"name": "family_parse", "desc": "Таблица семейств без сессии Creo: строки, вложенные таблицы, строки без файлов (байт-парсер, оба именования)", "params": {"q": "имя generic или путь"}, "approval": False, "fn": tool_family_parse})
'''

i = s.find("_FAMRUN")
s = s[:i] + NEW if i >= 0 else s + "\n" + NEW
fp.write_text(s, encoding="utf-8")
print("[+] find_tools: family_parse исправлен (Path, оба именования, вложенные)")
print("ГОТОВО: .\\AI_RESTART.bat, затем: family_parse q=pin_split и family_parse q=DF-STP2-VP")