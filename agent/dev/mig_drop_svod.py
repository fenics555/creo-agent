# -*- coding: utf-8 -*-
r"""mig_drop_svod — убрать свод из общей agent.sqlite, оставив мозг (Волна 1.2, шаг 2, финал).

ВНИМАНИЕ: необратимо. Запускать ТОЛЬКО когда агент остановлен (не пишет в общую) и читатели
свода уже переключены на svod (summary.sqlite). Удаляет сводные таблицы из общей + VACUUM.
Общая agent.sqlite -> мозг (~1 МБ). Свод живёт в summary.sqlite (схема svod).
"""
import os
import sqlite3
import sys
from pathlib import Path

MAIN = Path(r"D:\AI\tools\agent\data\agent.sqlite")
SVOD = ["files", "models", "model_embs", "bom", "links", "chunks", "fts_index"]
BRAIN = {"chat", "history", "trail_problems", "trail_scans", "skill_usage",
         "role_deny", "plm_statuses", "facts", "sqlite_sequence"}


def main():
    if not MAIN.exists():
        print("нет общей: %s" % MAIN)
        return 2
    # Защита: не трогать, если агент держит 8765 (мог бы писать).
    import socket
    try:
        s = socket.create_connection(("127.0.0.1", 8765), timeout=1); s.close()
        print("СТОП: агент жив на 8765 — сначала остановить (taskkill), иначе запись в общую.")
        return 3
    except Exception:
        pass
    c = sqlite3.connect(str(MAIN))
    before = os.path.getsize(str(MAIN))
    names = [r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    dropped = []
    for t in SVOD:
        if t in names:
            c.execute('DROP TABLE IF EXISTS "%s"' % t)
            dropped.append(t)
    # Остаточные shadow-таблицы fts5 (если DROP виртуальной не убрал).
    shadow = [r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'fts_index_%'")]
    for t in shadow:
        c.execute('DROP TABLE IF EXISTS "%s"' % t)
        dropped.append(t)
    c.commit()
    c.execute("VACUUM")
    c.commit()
    after = os.path.getsize(str(MAIN))
    left = sorted(r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
    c.close()
    print("общая: было %.1f МБ -> стало %.1f МБ (освобождено %.1f МБ)"
          % (before / 1048576, after / 1048576, (before - after) / 1048576))
    print("удалено (%d): %s" % (len(dropped), ", ".join(dropped) or "—"))
    print("осталось (мозг): %s" % ", ".join(left))
    foreign = [t for t in left if t not in BRAIN]
    print("ВНЕ зоны мозга (проверить!): %s" % (foreign or "нет — чисто"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
