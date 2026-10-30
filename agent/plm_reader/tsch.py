import sys, os, sqlite3, tempfile
sys.path.insert(0, r"D:\AI\tools\agent\plm_reader")
sys.path.insert(0, r"D:\AI\tools\agent\plm_reader\debug")
import engine as E
# создать тестовую базу со схемой
db=os.path.join(tempfile.gettempdir(),"_eng_test.db")
if os.path.exists(db): os.remove(db)
con=E.connect(db=db)
print("схема создана, таблиц:", len([r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]))
con.close()
print("таблицы:", sorted(r[0] for r in sqlite3.connect(db).execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")))
os.remove(db)
