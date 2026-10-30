import sqlite3
D=r"D:\AI\tools\agent\plm_reader\db\plm_reader.db"
c=sqlite3.connect(D); cur=c.cursor()
print("=== ТАБЛИЦЫ БОЕВОЙ БАЗЫ ===")
for n in [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]:
    cnt=cur.execute(f"SELECT COUNT(*) FROM [{n}]").fetchone()[0]
    print(f"  {n:<16} {cnt}")
print()
print("=== колонки snapshots (главная) ===")
print("  ", [r[1] for r in cur.execute("PRAGMA table_info(snapshots)")])
print("=== колонки params ===")
print("  ", [r[1] for r in cur.execute("PRAGMA table_info(params)")])
