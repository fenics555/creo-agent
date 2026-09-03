# -*- coding: utf-8 -*-
import os, sys, sqlite3
from pathlib import Path
AG = Path(r"D:\AI\tools\agent"); sys.path.insert(0, str(AG))
out = []
def P(s=""): out.append(str(s)); print(str(s))

P("== БАЗА ==")
dbf = AG / "data" / "agent.sqlite"
P("agent.sqlite: %s (%d МБ)" % (dbf.exists(), dbf.stat().st_size // 1048576 if dbf.exists() else 0))
if dbf.exists():
    c = sqlite3.connect(str(dbf))
    for t in ("models", "chunks", "files", "usage", "history"):
        try: P("  %s: %d" % (t, c.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]))
        except Exception as e: P("  %s: НЕТ (%s)" % (t, str(e)[:60]))
    c.close()

import settings, core
P("\n== КОРНИ СКАНА ==")
raw = settings.get("scan_roots")
P("config scan_roots = %s" % (raw,))
roots = core.read_roots() if hasattr(core, "read_roots") else (raw or [])
for r in roots:
    ex = os.path.exists(r); cnt = 0
    if ex:
        for dp, dn, fn in os.walk(r):
            cnt += len(fn)
            if cnt > 300000: break
    P("  %s : %s, файлов~%d" % (r, "ЕСТЬ" if ex else "НЕТ", cnt))

P("\n== SCANNER ==")
import scanner
for fn in ("scan_models", "index_all", "index_state", "tool_index_state"):
    P("  %s: %s" % (fn, hasattr(scanner, fn)))

P("\n== DIAG_TEST ==")
import tools_registry as TR
t = TR.get("diag_test")
P(t["fn"]() if t else "diag_test не найден")

P("\n== ЛОГ (хвост 25) ==")
try:
    for l in core.LOGF.read_text(encoding="utf-8", errors="ignore").splitlines()[-25:]: P("  " + l)
except Exception as e: P("лога нет: %s" % e)

(AG / "AUDIT_REPORT.txt").write_text("\n".join(out), encoding="utf-8")
P("\nГОТОВО: пришли содержимое D:\\AI\\tools\\agent\\AUDIT_REPORT.txt")