# -*- coding: utf-8 -*-
r"""
ТРАНСФОРМЕР v12 — БЭКАПЫ (backup.py)
Двухуровневые: рабочие копии sqlite каждые 6 часов + архив.
Глубина — из settings (retention).
"""
import time, datetime, threading, sqlite3, shutil
from core import log, DB, DATA_DIR
import settings

BK = DATA_DIR / "backups"
MANUAL_BK = DATA_DIR / "backup"

# ЖИВАЯ НАХОДКА 03.10.2026 (аудит data\, Д9): папок бэкапов ДВЕ — `backups` (авто, ротация
# по retention) и `backup` (ручные копии «перед правкой», 443 файла, ротации нет). Ручная
# растёт молча. Ниже — уборщик с dry-run по умолчанию: он НИЧЕГО не удаляет сам, только
# показывает, что можно убрать, и ждёт подтверждения словом `да`.
def sweep_manual(days=30, do=False):
    """Показать (и по `do=True` — удалить) ручные копии старше `days` дней.

    Безопасность: НИКОГДА не трогает `backups` (авто), `*.sqlite` (рабочая база) и папки
    `pre_data_audit_*`. По умолчанию только список — удаление требует явного `do=True`.
    """
    import time
    now = time.time()
    rows, freed = [], 0
    if not MANUAL_BK.exists():
        return "папки ручных бэкапов нет"
    for f in MANUAL_BK.rglob("*"):
        if not f.is_file():
            continue
        name = f.name.lower()
        if name.endswith(".sqlite") or f.name.startswith("pre_data_audit_"):
            continue                                   # рабочая база и страховка аудита
        age = (now - f.stat().st_mtime) / 86400.0
        if age < days:
            continue
        rows.append((age, f.stat().st_size, str(f)))
    rows.sort(reverse=True)
    for age, size, path in rows:
        if do:
            try:
                os.remove(path); freed += size
                log("ручной бэкап удалён: %s (%.1f МБ, %d дн.)" % (path, size / 1e6, age))
            except Exception as e:
                log("не удалил %s: %s" % (path, e))
    head = ("УДАЛЕНО %d файлов, освобождено %.1f МБ" % (len(rows), freed / 1e6)) if do \
        else ("НАЙДЕНО %d файлов старше %d дней (ничего не удалено — повтори с do=True)" % (len(rows), days))
    lines = [head]
    for age, size, path in rows[:20]:
        lines.append("  %5.1f дн. %8.1f КБ  %s" % (age, size / 1024.0, path))
    if len(rows) > 20:
        lines.append("  … и ещё %d" % (len(rows) - 20))
    return "\n".join(lines)

def _do():
    try:
        BK.mkdir(parents=True, exist_ok=True)
        if not DB.exists(): return
        name = "agent_%s.sqlite" % datetime.datetime.now().strftime("%y%m%d_%H%M")
        dst = BK / name
        src = sqlite3.connect(DB, timeout=30); dst_c = sqlite3.connect(dst)
        src.backup(dst_c); src.close(); dst_c.close()
        log("бэкап: %s" % name)
        keep = settings.get("retention") or 7
        olds = sorted(BK.glob("agent_*.sqlite"), key=lambda f: f.stat().st_mtime, reverse=True)
        for f in olds[keep:]: f.unlink(missing_ok=True)
    except Exception as e:
        log("бэкап err: %s" % e)

def _loop():
    while True:
        _do()
        time.sleep(6 * 3600)

def start():
    threading.Thread(target=_loop, daemon=True).start()

def restore(name):
    src = BK / name
    if not src.exists(): return "нет такого бэкапа"
    shutil.copyfile(src, DB)
    return "восстановлено из %s (перезапустите агента)" % name

def list_backups():
    if not BK.exists(): return "бэкапов нет"
    return "\n".join("• %s (%.1f МБ)" % (f.name, f.stat().st_size / 1e6) for f in sorted(BK.glob("agent_*.sqlite"), reverse=True))