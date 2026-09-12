# -*- coding: utf-8 -*-
import datetime
import core
import users

def _db():
    c = core.db()
    c.execute("CREATE TABLE IF NOT EXISTS chat(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, login TEXT, name TEXT, text TEXT)")
    return c

def chat_send(login, text):
    text = (text or "").strip()[:500]
    if not text:
        return {"ok": False, "msg": "пусто"}
    prof = users.get_profile(login) or {}
    c = _db()
    c.execute("INSERT INTO chat(ts,login,name,text) VALUES(?,?,?,?)",
              (datetime.datetime.now().strftime("%d.%m %H:%M"), login,
               prof.get("display_name", login), text))
    c.commit(); c.close()
    return {"ok": True}

def chat_poll(last):
    c = _db()
    rows = c.execute("SELECT id,ts,name,text FROM chat WHERE id>? ORDER BY id LIMIT 100", (int(last),)).fetchall()
    c.close()
    return [{"id": r[0], "ts": r[1], "name": r[2], "text": r[3]} for r in rows]

def tool_chat_last(**kw):
    rows = chat_poll(0)
    if not rows:
        return "в чате пусто"
    return "\n".join("%s %s: %s" % (m["ts"], m["name"], m["text"]) for m in rows[-15:])

TOOLS = [
    {"name": "chat_last", "desc": "Показать последние сообщения команды", "params": {}, "approval": False, "fn": tool_chat_last},
]