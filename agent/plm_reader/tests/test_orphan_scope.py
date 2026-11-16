# -*- coding: utf-8 -*-
"""Регресс-тест V206: (a) canon снимает хвостовую точку; (b) doctor делит «вне области скана»."""
import os
import shutil
import sqlite3
import sys
import tempfile

HERE = r"D:\AI\tools\agent\plm_reader"
sys.path.insert(0, HERE)
os.chdir(HERE)
import creo_read as C          # noqa: E402
import engine as E             # noqa: E402
import plm_database as DB      # noqa: E402

fails = []


def ck(name, got, want):
    ok = (got == want)
    print("%-46s %-6s got=%r" % (name, "OK" if ok else "FAIL", got))
    if not ok:
        fails.append(name)


ck("canon('0-2500.')", C.canon_model("0-2500."), "0-2500")
ck("canon('0-80.')", C.canon_model("0-80."), "0-80")
ck("canon('-.PRT') fragment", C.canon_model("-.PRT"), "")

tmp = tempfile.mkdtemp(prefix="v206_scope_")
db = os.path.join(tmp, "plm_reader.db")
con = sqlite3.connect(db)
con.executescript(E.SCHEMA)
con.execute("INSERT INTO snapshots(model,path) VALUES('AA','/a')")
con.execute("INSERT INTO items(item_key,model,folder) VALUES('k','BB','')")
con.executemany("INSERT INTO links(parent,child,qty,source,origin) VALUES(?,?,?,?,?)",
                [("AA", "CC", 1, "asm_comp", "real"),   # ни в snapshots, ни в items -> ВНЕ области
                 ("AA", "BB", 1, "asm_comp", "real")])  # в items, но не в snapshots -> живой
con.commit()
con.close()

doc = DB._doctor_data(db)
shutil.rmtree(tmp, ignore_errors=True)
lc = [o for o in doc["orphans"] if o["table"] == "links" and o["column"] == "child"]
o = lc[0] if lc else {}
ck("links.child real", o.get("real"), 2)
ck("links.child outside", o.get("outside"), 1)
ck("в orphans_outside есть links.child",
   any(x["table"] == "links" and x["column"] == "child" for x in doc.get("orphans_outside", [])), True)
ck("в orphans_live остался (real-outside>0)",
   any(x["table"] == "links" and x["column"] == "child" for x in doc.get("orphans_live", [])), True)

print("")
print("ИТОГ: " + ("ВСЁ ОК" if not fails else "ПРОВАЛЫ: " + ", ".join(fails)))
sys.exit(1 if fails else 0)
