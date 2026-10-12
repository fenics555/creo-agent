import sqlite3
c = sqlite3.connect('file:data/agent.sqlite?mode=ro', uri=True)
for n in ('bom','links'):
    s = c.execute("SELECT sql FROM sqlite_master WHERE name=?", (n,)).fetchone()
    print('TABLE', n); print(s[0]); print('---')
c.close()
