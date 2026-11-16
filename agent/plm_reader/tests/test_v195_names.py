# -*- coding: utf-8 -*-
"""Регресс-тест V195: ЧТО РЕАЛЬНО ПИШЕТ сканер (сквозная запись в ВРЕМЕННУЮ базу).

НЕ трогает боевую базу и шару Z: — работает только во временном файле %TEMP%.
Проверяет:
  1) stem()/canon_model() срезают .XPR и вспомогательные расширения;
  2) write_item() пишет ОДИНАКОВЫЙ ключ модели в snapshots/params/items (без .XPR);
  3) состав (links.child) — без расширения, без само-связи и без обрывков («-00»).
Выход: код 0 — всё ок, 1 — есть провалы. Итог печатается в stdout.
"""
import os
import sqlite3
import sys
import tempfile

HERE = r"D:\AI\tools\agent\plm_reader"
sys.path.insert(0, HERE)
os.chdir(HERE)
import engine as E          # noqa: E402
import creo_read as C       # noqa: E402
import plm_scanner as S     # noqa: E402

fails = []


def check(name, got, want):
    ok = (got == want)
    print("%-52s %-6s got=%r" % (name, "OK" if ok else "FAIL", got))
    if not ok:
        fails.append("%s: got=%r want=%r" % (name, got, want))


print("== 1) stem / canon_model ==")
check("stem('er20-a.xpr')", C.stem("er20-a.xpr"), "ER20-A")
check("stem('DF.PRT.2')", C.stem("DF.PRT.2"), "DF")
check("stem('x.m_p')", C.stem("x.m_p"), "X")
check("stem('y.tph')", C.stem("y.tph"), "Y")
check("canon('er20-a.xpr')", C.canon_model("er20-a.xpr"), "ER20-A")
check("canon('-00.PRT') fragment", C.canon_model("-00.PRT"), "")

db = os.path.join(tempfile.gettempdir(), "v195_test.db")
for suf in ("", "-wal", "-shm", "-journal"):
    try:
        os.remove(db + suf)
    except OSError:
        pass
con = sqlite3.connect(db)
con.executescript(E.SCHEMA)
con.commit()

print("== 2) запись .XPR (ключ без расширения) ==")
S.write_item(con, r"Z:\T\er20-a.xpr",
             {"snapshots": {"model": "ER20-A"}, "params": [("N", "v")], "links": {}})

print("== 3) связь: само-компонент (.asm) и обрывок (.drw) ==")
S.write_item(con, r"Z:\T\self.asm",
             {"snapshots": {}, "params": [],
              "links": {"components": [{"name": "PART.PRT", "count": 1},
                                       {"name": "SELF.ASM", "count": 1}]}})
S.write_item(con, r"Z:\T\real.drw",
             {"snapshots": {}, "params": [],
              "links": {"model_names": ["-00.PRT", "MODELL.PRT"]}})
con.commit()

snap = con.execute("SELECT model FROM snapshots WHERE path=?", (r"Z:\T\er20-a.xpr",)).fetchone()
check("snapshots.model (xpr)", snap[0] if snap else None, "ER20-A")
pm = [r[0] for r in con.execute("SELECT DISTINCT model FROM params WHERE path=?",
                                (r"Z:\T\er20-a.xpr",)).fetchall()]
check("params.model (xpr)", pm, ["ER20-A"])
it = con.execute("SELECT model FROM items WHERE item_key LIKE ?", (r"%er20-a.xpr",)).fetchone()
check("items.model (xpr)", it[0] if it else None, "ER20-A")
ch = [r[0] for r in con.execute("SELECT child FROM links WHERE parent='SELF' ORDER BY child").fetchall()]
check("links(asm).child", ch, ["PART"])
cd = [r[0] for r in con.execute("SELECT child FROM links WHERE parent='REAL' ORDER BY child").fetchall()]
check("links(drw).child", cd, ["MODELL"])
selfl = con.execute("SELECT COUNT(*) FROM links WHERE parent=child").fetchone()[0]
check("self-links (должно быть 0)", selfl, 0)
con.close()

for suf in ("", "-wal", "-shm", "-journal"):
    try:
        os.remove(db + suf)
    except OSError:
        pass

print("== 4) достроитель связей: само-связь не создаётся ==")
db2 = os.path.join(tempfile.gettempdir(), "v195_bl.db")
for suf in ("", "-wal", "-shm", "-journal"):
    try:
        os.remove(db2 + suf)
    except OSError:
        pass
c2 = sqlite3.connect(db2)
c2.executescript(E.SCHEMA)
c2.executemany("INSERT INTO snapshots(model,path) VALUES(?,?)", [("A", "/a"), ("B", "/b")])
c2.executemany(
    "INSERT INTO links(parent,child,qty,source,origin) VALUES(?,?,?,?,?)",
    [("X.PRT", "X.PRT.2", 1, "asm_comp", "real"),   # canon схлопнет оба в 'X' -> само-связь
     ("A", "B", 1, "asm_comp", "real")])
c2.commit()
c2.close()
os.environ["PLM_DB"] = db2
try:
    import plm_build_links as L
    L.build(engine_mod=E)
    c3 = sqlite3.connect(db2)
    n_self = c3.execute("SELECT COUNT(*) FROM links WHERE origin='built' AND parent=child").fetchone()[0]
    n_back = c3.execute("SELECT COUNT(*) FROM links WHERE origin='built' AND parent='B' AND child='A'").fetchone()[0]
    c3.close()
    check("built self-links (должно быть 0)", n_self, 0)
    check("built обратная связь B->A есть", n_back, 1)
except Exception as e:                       # noqa: BLE001
    check("build_links(self-guard)", "ошибка: %s" % e, "ok")
finally:
    os.environ.pop("PLM_DB", None)
for suf in ("", "-wal", "-shm", "-journal"):
    try:
        os.remove(db2 + suf)
    except OSError:
        pass

print("")
print("ИТОГ: " + ("ВСЁ ОК" if not fails else "ПРОВАЛЫ: " + "; ".join(fails)))
sys.exit(1 if fails else 0)
