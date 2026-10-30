import sqlite3
D=r"D:\AI\tools\agent\plm_reader\db\plm_reader.db"
c=sqlite3.connect(D); cur=c.cursor()
print("=== ОДНОИМЁННЫЕ МОДЕЛИ (в разных папках) ===")
r=cur.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
u=cur.execute("SELECT COUNT(DISTINCT model) FROM snapshots").fetchone()[0]
print(f"  записей: {r} · уникальных имён: {u} · разница: {r-u}")
print()
print("=== ТОП одноимённых ===")
for m,cn in cur.execute("SELECT model,COUNT(*) c FROM snapshots GROUP BY model HAVING c>1 ORDER BY c DESC LIMIT 10"):
    print(f"  {m:<32} {cn} файлов")
print()
print("=== пример: папки одной модели ===")
for r in cur.execute("SELECT path FROM snapshots WHERE model=(SELECT model FROM snapshots GROUP BY model HAVING COUNT(*)>1 ORDER BY COUNT(*) DESC LIMIT 1) LIMIT 4"):
    print("  ", r[0])
