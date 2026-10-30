import sqlite3
D=r"D:\AI\tools\agent\plm_reader\db\plm_reader.db"
c=sqlite3.connect(D); cur=c.cursor()
print("=== что есть для уникальности ===")
print("snapshots: path · model · folder · size · mtime · rev  ← ЕСТЬ!")
print()
print("=== есть ли таблица папок? ===")
print("  folders:", cur.execute("SELECT COUNT(*) FROM folders").fetchone()[0])
print("  ", [r[1] for r in cur.execute("PRAGMA table_info(folders)")])
print()
print("=== сколько РАЗНЫХ папок у одноимённых? ===")
r=cur.execute("SELECT COUNT(DISTINCT folder) FROM snapshots").fetchone()[0]
print(f"  разных папок: {r}")
print()
print("=== версии: есть ли в path? ===")
for r in cur.execute("SELECT path FROM snapshots WHERE model='CTKD-PSB-04-01' LIMIT 6"):
    print("  ", r[0].split(chr(92))[-1])
