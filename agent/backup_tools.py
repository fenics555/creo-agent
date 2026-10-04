# -*- coding: utf-8 -*-
"""АГЕНТ v12 — БЛОК БЭКАПОВ (backup_tools.py). Направление: архив базы."""
import backup as BK
import core
import settings

def tool_list(**kw): return BK.list_backups()
def tool_restore(name="", **kw): return BK.restore(name)

def tool_housekeeping():
    import os, datetime
    rep = []
    # ЖИВАЯ НАХОДКА 02.10.2026 (аудит agent\data): тут стояло core.BASE / "data" — это
    # D:\AI\tools\data, папка ПУСТАЯ (наследие старой вёрстки дома). Настоящие бэкапы агента
    # лежат в agent\data\backups (их кладёт backup.py через DATA_DIR), а картинки — в
    # agent\data\pdfcache. Уборка молча делала НИЧЕГО: пути не существовали.
    # Правило: источник пути — один (core.DATA_DIR), как и база.
    bak = core.DATA_DIR / "backups"
    keep = int(settings.get("retention") or 7)
    if bak.exists():
        fs = sorted(bak.glob("*.sqlite*"), key=os.path.getmtime, reverse=True)
        for f in fs[keep:]:
            f.unlink(); rep.append("backup removed " + f.name)
    else:
        rep.append("ВНИМАНИЕ: папки бэкапов нет: %s" % bak)
    days = int(settings.get("image_days") or 7)
    cut = datetime.datetime.now().timestamp() - days * 86400
    pc = core.DATA_DIR / "pdfcache"
    if pc.exists():
        for f in pc.glob("*.png"):
            if os.path.getmtime(f) < cut:
                f.unlink(); rep.append("cache removed " + f.name)
    # ЖИВАЯ НАХОДКА 02.10.2026 (аудит agent\data): таблица feedback создаётся ЛЕНИВО —
    # только когда человек первый раз нажмёт «оценка» в витрине. Пока её нет, ночная
    # задача backup падала на этом DELETE, и вместе с ней откатывался prune истории
    # (commit был ниже), а VACUUM не доходил. Правило: уборка не должна падать из-за
    # того, что кто-то ещё не нажал кнопку; отсутствующую таблицу просто пропускаем.
    c = core.db()
    # 04.10.2026 (аудит настроек): `history_days` («дней хранить историю») и `client_days`
    # («дней хранить сессии») были объявлены, но уборка шла по зашитым 90 и 180 дням — обе были
    # обещанием впустую. Теперь срок истории берётся из настройки; таблица feedback (её ещё
    # может не быть) чистится по `client_days` — столько дней храним отзывы клиентов.
    try:
        hist_days = int(settings.get("history_days") or 365)
    except Exception:
        hist_days = 365
    try:
        cli_days = int(settings.get("client_days") or 365)
    except Exception:
        cli_days = 365
    c.execute("DELETE FROM history WHERE ts < datetime('now','-%d days')" % max(1, hist_days))
    _fb = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE name='feedback'")]
    if _fb:
        c.execute("DELETE FROM feedback WHERE ts < datetime('now','-%d days')" % max(1, cli_days))
        rep.append("history/feedback pruned (%d/%d дней)" % (hist_days, cli_days))
    else:
        rep.append("history pruned (%d дней; таблицы feedback ещё нет — пропущено)" % hist_days)
    c.commit(); c.close()
    try:
        c2 = core.db()
        c2.execute("VACUUM")
        c2.close()
        rep.append("sqlite vacuum done")
    except Exception as e:
        # VACUUM не проходит, если базу держит живое соединение агента — это не повод
        # ронять ночную уборку целиком.
        rep.append("VACUUM пропущен: %s" % str(e)[:80])
    return "\n".join(rep) or "housekeeping: чисто"

def _has_fts(c):
    """Есть ли таблица индекса знаний (FTS5)."""
    try:
        return bool(c.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='fts_index'").fetchone()[0])
    except Exception:
        return False


def tool_drift_check():
    import os
    rep = []
    c = core.db()
    exts = (".prt", ".asm", ".drw", ".pdf")
    pats = ["%" + e for e in exts]
    db_n = c.execute("SELECT COUNT(*) FROM files WHERE " + " OR ".join(["lower(path) LIKE ?"] * len(exts)), pats).fetchone()[0]
    ch_n = c.execute("SELECT COUNT(*) FROM fts_index").fetchone()[0] if _has_fts(c) else 0
    c.close()
    disk_n = 0
    _rr = settings.get("scan_roots") or []
    if isinstance(_rr, str):
        _rr = _rr.split(",")
    for r in [x.strip() for x in _rr if x and x.strip()]:
        if not os.path.isdir(r):
            continue
        for w, _, fs in os.walk(r):
            for f in fs:
                if f.lower().endswith(exts):
                    disk_n += 1
    if disk_n == 0:
        rep.append("ROOTS: моделей под scan_roots нет (инвентарь моделей ведёт harvest.db) — сверка файлов пропущена")
    drift = abs(disk_n - db_n) * 100 // max(disk_n, 1)
    rep.append("files: db %d, disk %d, drift %d%%" % (db_n, disk_n, drift))
    if drift > 5:
        rep.append("DRIFT ALARM: файловый индекс разошёлся с диском, нужен scan")
    if ch_n == 0:
        rep.append("CHUNKS ALARM: база знаний пуста, нужен index")
    return "\n".join(rep)

TOOLS = [
    {"name": "backup_list", "desc": "Список бэкапов базы", "params": {}, "approval": False, "fn": tool_list},
    {"name": "backup_restore", "desc": "Восстановить базу из бэкапа", "params": {"name": "имя файла"}, "approval": True, "fn": tool_restore},
    {"name": "backup_housekeeping", "desc": "Ночная уборка: бекапы до retention, pdfcache по image_days, prune истории", "params": {}, "fn": tool_housekeeping},
    {"name": "drift_check", "desc": "Сверка баз с диском: файлы и чанки, аварийные строки", "params": {}, "fn": tool_drift_check},
]
