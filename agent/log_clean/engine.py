# -*- coding: utf-8 -*-
"""log_clean — движок уборки логов (автономная программа, класс Р).

Что делает: смотрит каталоги `D:\\AI\\log\\<имя>\\` и убирает файлы старше срока хранения.
Сроки — в `D:\\AI\\log\\retention.json` (тот же файл читает ночной цикл агента, поэтому цифры одни на всех).

Правила (важные):
  * по умолчанию НЕ удаляем навсегда, а уносим в корзину `D:\\AI\\log\\_trash_clean\\<дата>\\` (можно вернуть);
  * файл, который сейчас открыт (залочен) — пропускаем, пишем причину в отчёт;
  * сам `retention.json`, корзину и свой журнал не трогаем никогда.

API: scan(root) -> список записей; clean(root, mode, days_default) -> отчёт; get_retention/save_retention.
"""
import datetime
import json
import os
import shutil
import time
from pathlib import Path

LOG_ROOT = Path(r"D:\AI\log")
RETENTION_FILE = LOG_ROOT / "retention.json"
PROG_DIR = Path(__file__).resolve().parent
TRASH = LOG_ROOT / "_trash_clean"
DEFAULT_DAYS = 30
NEVER = {"_trash_clean", "log_clean"}          # свои каталоги — не трогаем


def get_retention():
    try:
        with open(RETENTION_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def save_retention(d):
    RETENTION_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RETENTION_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1, sort_keys=True)


def is_locked(path):
    """Занят ли файл другим процессом. Надёжный приём для Windows: переименовать в себя же;
    если файл открыт на запись — операция не пройдёт. Прежний способ (open 'a') оставлен как запасной."""
    try:
        os.rename(str(path), str(path))
        return False
    except OSError:
        pass
    try:
        with open(path, "a"):
            return False
    except OSError:
        return True


def scan(root=None, days_default=DEFAULT_DAYS):
    """План уборки: по каждому каталогу — сколько файлов и что старше срока."""
    root = Path(root or LOG_ROOT)
    retention = get_retention()
    now = time.time()
    out = []
    if not root.exists():
        return out
    for sub in sorted(root.iterdir()):
        if not sub.is_dir() or sub.name in NEVER:
            continue
        days = days_default if sub.name not in retention else retention[sub.name]
        rec = {"folder": sub.name, "path": str(sub), "days": days, "files": 0,
               "old": 0, "old_bytes": 0, "locked": 0, "newest": "", "oldest": ""}
        times = []
        for f in sub.glob("*"):
            if not f.is_file():
                continue
            rec["files"] += 1
            st = f.stat()
            times.append(st.st_mtime)
            age_days = (now - st.st_mtime) / 86400
            if age_days > days:
                if is_locked(f):
                    rec["locked"] += 1
                else:
                    rec["old"] += 1
                    rec["old_bytes"] += st.st_size
        if times:
            rec["newest"] = datetime.datetime.fromtimestamp(max(times)).strftime("%d.%m.%Y")
            rec["oldest"] = datetime.datetime.fromtimestamp(min(times)).strftime("%d.%m.%Y")
        out.append(rec)
    return out


def clean(root=None, mode="trash", days_default=DEFAULT_DAYS, report=True):
    """mode='trash' — унести в корзину (по умолчанию), mode='delete' — удалить навсегда.
    Возвращает отчёт: что сделано, сколько файлов и байт, что пропущено и почему."""
    root = Path(root or LOG_ROOT)
    retention = get_retention()
    now = time.time()
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
    trash_dir = (root / "_trash_clean") / stamp
    rep = {"когда": stamp, "каталог": str(root), "режим": mode, "перенесено": [], "удалено": [],
           "пропущено": [], "байт": 0}
    for sub in sorted(root.iterdir()):
        if not sub.is_dir() or sub.name in NEVER:
            continue
        days = days_default if sub.name not in retention else retention[sub.name]
        for f in sub.glob("*"):
            if not f.is_file():
                continue
            st = f.stat()
            if (now - st.st_mtime) / 86400 <= days:
                continue
            if is_locked(f):
                rep["пропущено"].append("%s / %s: файл занят" % (sub.name, f.name))
                continue
            try:
                if mode == "delete":
                    size = st.st_size
                    f.unlink()
                    rep["удалено"].append("%s / %s" % (sub.name, f.name))
                else:
                    dst_dir = trash_dir / sub.name
                    dst_dir.mkdir(parents=True, exist_ok=True)
                    size = st.st_size
                    shutil.move(str(f), str(dst_dir / f.name))
                    rep["перенесено"].append("%s / %s" % (sub.name, f.name))
                rep["байт"] += size
            except Exception as e:
                rep["пропущено"].append("%s / %s: %s" % (sub.name, f.name, e))
    if report:
        prog_log = LOG_ROOT / "log_clean"
        prog_log.mkdir(parents=True, exist_ok=True)
        with open(prog_log / ("run_%s.json" % stamp), "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=1)
    return rep


def trash_cleanup(days=7, root=None):
    """Корзина тоже не вечна: убираем из неё каталоги старше `days` дней."""
    gone = []
    trash = Path(root) / "_trash_clean" if root else TRASH
    if not trash.exists():
        return gone
    now = time.time()
    for d in trash.iterdir():
        if not d.is_dir():
            continue
        try:
            if (now - d.stat().st_mtime) / 86400 > days:
                shutil.rmtree(d)
                gone.append(d.name)
        except Exception:
            pass
    return gone


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Уборка логов по срокам хранения (класс Р)")
    p.add_argument("--root", default=str(LOG_ROOT))
    p.add_argument("--days", type=int, default=DEFAULT_DAYS)
    p.add_argument("--apply", action="store_true", help="без флага только план")
    p.add_argument("--delete", action="store_true", help="удалять навсегда (по умолчанию — в корзину)")
    p.add_argument("--trash-days", type=int, default=7, help="сколько дней держать корзину")
    a = p.parse_args()
    if a.apply:
        r = clean(a.root, "delete" if a.delete else "trash", a.days)
        print("сделано: перенесено %d, удалено %d, пропущено %d, освобождено %.1f МБ"
              % (len(r["перенесено"]), len(r["удалено"]), len(r["пропущено"]), r["байт"] / 1048576))
        for g in trash_cleanup(a.trash_days):
            print("корзина: убран старый каталог %s" % g)
    else:
        for rec in scan(a.root, a.days):
            print("%-20s файлов %-5d старше %s дн.: %-4d (%.1f МБ), занятых %d  [%s … %s]"
                  % (rec["folder"], rec["files"], rec["days"], rec["old"],
                     rec["old_bytes"] / 1048576, rec["locked"], rec["oldest"], rec["newest"]))