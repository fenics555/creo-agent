# -*- coding: utf-8 -*-
"""timeline_tools: build timeline events for a model."""
import os
import core

def build_timeline(name, window_days=7):
    events = []
    c = core.db()
    row = c.execute("SELECT path, mtime FROM files WHERE path LIKE ?",
                    ("%" + name + "%",)).fetchone()
    if row:
        events.append({"date": row[1], "kind": "self", "label": name,
                       "detail": "\u043c\u043e\u0434\u0435\u043b\u044c \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0430", "path": row[0]})
        d = os.path.dirname(row[0])
        t0 = row[1] - window_days * 86400
        t1 = row[1] + window_days * 86400
        for r in c.execute("SELECT path, mtime FROM files WHERE path LIKE ? AND mtime BETWEEN ? AND ?",
                           (d + "%", t0, t1)).fetchall():
            if r[0] != row[0]:
                events.append({"date": r[1], "kind": "neighbor",
                               "label": os.path.basename(r[0]),
                               "detail": "\u0441\u043e\u0441\u0435\u0434\u043d\u0438\u0439 \u0444\u0430\u0439\u043b", "path": r[0]})
    for r in c.execute("SELECT ts, q, client FROM history WHERE q LIKE ? ORDER BY ts DESC LIMIT 20",
                       ("%" + name + "%",)).fetchall():
        events.append({"date": r[0], "kind": "ask", "label": r[2] or "?",
                       "detail": r[1][:80], "path": ""})
    c.close()
    events.sort(key=lambda e: e["date"], reverse=True)
    return {"events": events, "center": name, "window_days": window_days}

TOOLS = [{"name": "timeline", "desc": "\u0412\u0440\u0435\u043c\u0435\u043d\u043d\u0430\u044f \u0448\u043a\u0430\u043b\u0430 \u043c\u043e\u0434\u0435\u043b\u0438", "params": {"name": "\u0438\u043c\u044f"}, "fn": build_timeline}]
