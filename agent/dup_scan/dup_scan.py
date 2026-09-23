# -*- coding: utf-8 -*-
"""ДВОЙНИКИ (dup_scan) — отдельная программа класса Р: ищет одинаковые файлы по содержимому.
Creo и агент НЕ нужны. Ничего не удаляет: в режиме --apply переносит лишние копии в _trash_dup.

Запуск:
  dup_scan.py <папка> [ещё папки...] [--min-mb N] [--ext prt,asm,drw,pdf] [--apply]
Отчёт: консоль + D:\\AI\\log\\dup_scan\\run_<дата>_<время>.txt
"""
import hashlib
import os
import re
import sys
import time

# Вывод в консоль делаем кодировко-устойчивым: в cp1251/cp866 нет стрелки «→», и print падал
# в самом конце режима --apply (перенос уже сделан, а программа завершалась ошибкой). Живая находка 23.09.2026.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

LOG_DIR = r"D:\AI\log\dup_scan"
SKIP_DIRS = {"_trash", "_trash_dup", ".git", "__pycache__", "node_modules", "backup", "backups"}
CREO_EXT = ("prt", "asm", "drw", "frm", "sec", "lay", "mfg", "xpr", "xas", "cgr", "neu", "stp")


def logical_ext(fn):
    """Расширение с учётом Creo-версий: x.prt.1 -> prt; обычное x.pdf -> pdf."""
    low = fn.lower()
    m = re.match(r"^.*\.(" + "|".join(CREO_EXT) + r")\.\d+$", low)
    if m:
        return m.group(1)
    return os.path.splitext(low)[1].lstrip(".")


def log_open():
    os.makedirs(LOG_DIR, exist_ok=True)
    p = os.path.join(LOG_DIR, "run_%s.txt" % time.strftime("%Y-%m-%d_%H%M"))
    return open(p, "w", encoding="utf-8"), p


def sha1(path, buf=1024 * 1024):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        while True:
            b = f.read(buf)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def walk(roots, exts, min_bytes):
    """Список (путь, размер, mtime) — только файлы нужных расширений и размера."""
    out = []
    for root in roots:
        if not os.path.isdir(root):
            print("нет папки: %s" % root)
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS]
            for fn in filenames:
                if exts and logical_ext(fn) not in exts:
                    continue
                full = os.path.join(dirpath, fn)
                try:
                    st = os.stat(full)
                except OSError:
                    continue
                if st.st_size < min_bytes:
                    continue
                out.append((full, st.st_size, st.st_mtime))
    return out


def find_dups(roots, exts=None, min_bytes=0, progress=None):
    """Ищет двойников и ВОЗВРАЩАЕТ результат структурой (ничего не печатает и не двигает) —
    это точка входа для окна программы.
    {'files': N, 'size_groups': K, 'groups': [{'size': b, 'keep': (путь, mtime), 'extra': [...]}],
     'waste': байт, 'errors': [...]}"""
    exts = {x.lower().lstrip(".") for x in exts} if exts else set()

    def say(s):
        if progress:
            progress(s)

    files = walk(roots, exts, int(min_bytes))
    say("файлов к проверке: %d" % len(files))
    by_size = {}
    for p, sz, mt in files:
        by_size.setdefault(sz, []).append((p, mt))
    cand = [v for v in by_size.values() if len(v) > 1]
    say("групп одинакового размера: %d (в них файлов %d)" % (len(cand), sum(len(v) for v in cand)))
    groups, errors = {}, []
    for grp in cand:
        for p, mt in grp:
            try:
                groups.setdefault(sha1(p), []).append((p, mt))
            except OSError as e:
                errors.append("не прочитать: %s (%s)" % (p, e))
    res = {"files": len(files), "size_groups": len(cand), "groups": [], "waste": 0, "errors": errors}
    for _h, items in groups.items():
        if len(items) < 2:
            continue
        items.sort(key=lambda x: -x[1])          # образец — самый свежий
        keep, extra = items[0], items[1:]
        size = os.path.getsize(keep[0])
        res["groups"].append({"size": size, "keep": keep, "extra": extra})
        res["waste"] += size * len(extra)
    res["groups"].sort(key=lambda g: -g["size"])
    return res


def move_extras(items):
    """Переносит файлы-двойники в `_trash_dup` рядом с ними (ничего не удаляет).
    Возвращает (сколько перенесено, [(путь, причина), ...])."""
    moved, errs = 0, []
    for p, _mt in items:
        trash = os.path.join(os.path.dirname(p), "_trash_dup")
        try:
            os.makedirs(trash, exist_ok=True)
            dst = os.path.join(trash, os.path.basename(p))
            n = 1
            while os.path.exists(dst):
                dst = os.path.join(trash, "%s_%d%s" % (os.path.splitext(os.path.basename(p))[0], n,
                                                       os.path.splitext(p)[1]))
                n += 1
            os.replace(p, dst)
            moved += 1
        except OSError as e:
            errs.append((p, str(e)))
    return moved, errs


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    roots, exts, min_mb, apply_ = [], set(), 0.0, False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--apply":
            apply_ = True
        elif a == "--min-mb":
            i += 1
            min_mb = float(argv[i])
        elif a == "--ext":
            i += 1
            exts = {x.strip().lower().lstrip(".") for x in argv[i].split(",") if x.strip()}
        else:
            roots.append(a.replace('"', ""))
        i += 1
    if not roots:
        print("укажи хотя бы одну папку")
        return 2

    f, logp = log_open()

    def out(s):
        print(s)
        f.write(s + "\n")
        f.flush()

    out("=== ДВОЙНИКИ (по содержимому, sha1) ===")
    out("папки: %s" % "; ".join(roots))
    out("фильтр: %s | от %.1f МБ | режим: %s" % (", ".join(sorted(exts)) or "все файлы", min_mb,
                                                "ПЕРЕНОС В _trash_dup" if apply_ else "только отчёт"))
    t0 = time.time()
    res = find_dups(roots, exts, int(min_mb * 1024 * 1024),
                    progress=lambda s: out("%s (%.1f с)" % (s, time.time() - t0)))
    for e in res["errors"]:
        out("  " + e)
    out("\nГРУПП ДВОЙНИКОВ: %d" % len(res["groups"]))

    moved = 0
    for g in res["groups"]:
        keep, extra = g["keep"], g["extra"]
        out("\n  ОБРАЗЕЦ: %s  (%.1f МБ, %s)" % (keep[0], g["size"] / 1048576.0,
                                               time.strftime("%d.%m.%Y %H:%M", time.localtime(keep[1]))))
        for p, _mt in extra:
            out("    двойник: %s" % p)
        if apply_:
            for one in extra:
                _n, errs = move_extras([one])
                if errs:
                    out("      НЕ перенесён: %s" % errs[0][1])
                else:
                    out("      → перенесён в _trash_dup: %s" % os.path.basename(one[0]))
                    moved += 1

    out("\nИТОГ: двойников %d, лишнего объёма %.2f ГБ, перенесено %d" %
        (sum(len(g["extra"]) for g in res["groups"]), res["waste"] / 1073741824.0, moved))
    out("отчёт: %s" % logp)
    f.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))