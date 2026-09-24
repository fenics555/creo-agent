# -*- coding: utf-8 -*-
"""log_clean — движок уборки логов (автономная программа, класс Р).

Что делает: смотрит каталоги `D:\\AI\\log\\<имя>\\` и убирает файлы старше срока хранения.
Сроки — в `D:\\AI\\log\\retention.json` (тот же файл читает ночной цикл агента, поэтому цифры одни на всех).

Правила (важные):
  * по умолчанию НЕ удаляем навсегда, а уносим в корзину `D:\\AI\\log\\_trash_clean\\<дата>\\` (можно вернуть);
  * файл, который сейчас открыт (залочен) — пропускаем, пишем причину в отчёт;
  * сам `retention.json`, корзину и свой журнал не трогаем никогда;
  * считаем ВЛОЖЕННЫЕ папки (`urn\\<исполнитель>\\`, `reports\\<тема>\\`) и файлы прямо в корне `log`
    (живая находка 24.09.2026: раньше до них не доходило — обещанные 14/28 дней не работали);
  * вложенную структуру сохраняем и в корзине, чтобы файлы с одинаковыми именами не перетирались.

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
NEVER_FILES = {"retention.json"}               # служебные файлы корня log
ROOT_LABEL = "root"                            # псевдокаталог: файлы прямо в D:\AI\log


def _files_of(sub):
    """Все файлы каталога, ВКЛЮЧАЯ вложенные (урна и отчёты держат подпапки по темам)."""
    for f in sorted(sub.rglob("*")):
        if f.is_file() and f.name not in NEVER_FILES:
            yield f


def _targets(root, days_default=DEFAULT_DAYS):
    """Что убираем и с каким сроком: подпапки log по retention.json + файлы в корне log.

    ЖИВАЯ НАХОДКА 24.09.2026: раньше брали только файлы в подпапках ПЕРВОГО уровня, поэтому
    содержимое `urn\\<исполнитель>\\` (обещали 14 дней) и `reports\\creoson_crashes\\` (28 дней)
    не убиралось никогда, а 15 МБ в корне log не видел никто."""
    r = get_retention()
    for sub in sorted(root.iterdir()):
        if not sub.is_dir() or sub.name in NEVER:
            continue
        days = days_default if sub.name not in r else r[sub.name]
        yield sub.name, sub, days, list(_files_of(sub))
    rf = [f for f in sorted(root.glob("*")) if f.is_file() and f.name not in NEVER_FILES]
    if rf:
        yield ROOT_LABEL, root, r.get(ROOT_LABEL, days_default), rf


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
    """План уборки: по каждому каталогу — сколько файлов и что старше срока.

    Файлы считаем ВКЛЮЧАЯ вложенные (см. `_targets`) и файлы прямо в корне log."""
    root = Path(root or LOG_ROOT)
    now = time.time()
    out = []
    if not root.exists():
        return out
    for label, folder, days, files in _targets(root, days_default):
        rec = {"folder": label, "path": str(folder), "days": days, "files": len(files),
               "old": 0, "old_bytes": 0, "locked": 0, "newest": "", "oldest": ""}
        times = []
        for f in files:
            try:
                st = f.stat()
            except OSError:
                continue
            times.append(st.st_mtime)
            if (now - st.st_mtime) / 86400 > days:
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
    Возвращает отчёт: что сделано, сколько файлов и байт, что пропущено и почему.

    Вложенные папки сохраняются и в корзине: иначе одноимённые `out.txt` из разных тем
    перетирали бы друг друга и вернуть файл было бы нельзя."""
    root = Path(root or LOG_ROOT)
    now = time.time()
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
    trash_dir = (root / "_trash_clean") / stamp
    rep = {"когда": stamp, "каталог": str(root), "режим": mode, "перенесено": [], "удалено": [],
           "пропущено": [], "байт": 0}
    for label, folder, days, files in _targets(root, days_default):
        for f in files:
            try:
                st = f.stat()
            except OSError as e:
                rep["пропущено"].append("%s / %s: %s" % (label, f.name, e)); continue
            if (now - st.st_mtime) / 86400 <= days:
                continue
            if is_locked(f):
                rep["пропущено"].append("%s / %s: файл занят" % (label, f.name))
                continue
            try:
                rel = f.relative_to(folder)
                if mode == "delete":
                    size = st.st_size
                    f.unlink()
                    rep["удалено"].append("%s / %s" % (label, rel.as_posix()))
                else:
                    dst = trash_dir / label / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    size = st.st_size
                    shutil.move(str(f), str(dst))
                    rep["перенесено"].append("%s / %s" % (label, rel.as_posix()))
                rep["байт"] += size
            except Exception as e:
                rep["пропущено"].append("%s / %s: %s" % (label, f.name, e))
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