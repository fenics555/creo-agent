# -*- coding: utf-8 -*-
r"""PDF БЕЗ МОДЕЛИ РЯДОМ (или модель в другой папке) — быстрая проверка.
Ходит по папке и подпапкам, берёт каждый PDF и смотрит: лежит ли рядом модель
(<имя>.drw/.prt/.asm/.frm[.N]). Если нет — ищет это имя в домашнем индексе агента
(agent.sqlite: models 44 тыс.; harvest.db: models_raw 93 тыс.), чтобы сказать, ГДЕ модель.

Запуск:
    python creo_pdf_orphans.py <папка> [--limit 200] [--quiet]
"""
import os, re, sqlite3, sys, time

MODEL_EXT = ("drw", "prt", "asm", "frm")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import creo_pdf_env as env                                   # noqa: E402
# Пути баз — из единого источника (инструмент может лежать на любом диске)
DBS = env.find_db_files()


def _short(s, w):
    s = os.path.basename(os.path.normpath(s)) or s
    return s if len(s) <= w else s[:w - 1] + "…"


def _kb(n):
    return ("%.0f КБ" % (n / 1024)) if n < 1048576 else ("%.1f МБ" % (n / 1048576))


def find_model_near(folder, base):
    """Есть ли в папке файл модели с этим базовым именем (любая версия)."""
    rx = re.compile(r"^" + re.escape(base) + r"\.(?:%s)(?:\.\d+)?$" % "|".join(MODEL_EXT), re.I)
    try:
        for n in os.listdir(folder):
            if rx.match(n):
                return n
    except Exception:
        pass
    return None


def _like_esc(s):
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


MODEL_RX = re.compile(r"\.(?:drw|prt|asm|frm)(?:\.\d+)?$", re.I)


def db_lookup(names):
    """Где искать модели: домашний индекс.
    В базах `name` = ПОЛНОЕ имя файла с расширением и версией (напр. 'x.prt.1'),
    поэтому ищем по префиксу '<база>.%'. names -> {lower(base): [path, ...]}"""
    found = {}
    for db, table in DBS:
        if not os.path.exists(db) or not names:
            continue
        try:
            c = sqlite3.connect("file:%s?mode=ro" % db.replace("\\", "/"), uri=True)
            cols = [d[1] for d in c.execute("PRAGMA table_info(%s)" % table)]
            if "name" not in cols or "path" not in cols:
                c.close(); continue
            sql = "SELECT name, path FROM %s WHERE lower(name) LIKE ? ESCAPE '\\'" % table
            for key in list(names):
                if key in found:
                    continue
                try:
                    rows = c.execute(sql, (_like_esc(key) + ".%",)).fetchall()
                except Exception:
                    continue
                hits = [str(r[1]) for r in rows if MODEL_RX.search(str(r[0]))]
                if hits:
                    found[key] = sorted(set(hits))
            c.close()
        except Exception as e:
            print("  (база %s недоступна: %s)" % (os.path.basename(db), e))
    return found


def scan(root, limit=200, quiet=False, apply_trash=False):
    t0 = time.time()
    pdfs, checked = [], 0
    t_last = time.time()
    for dirpath, dirnames, filenames in os.walk(root):
        for n in filenames:
            if n.lower().endswith(".pdf"):
                pdfs.append((dirpath, n))
            checked += 1
        if checked % 2000 == 0 and not quiet and time.time() - t_last > 5:
            t_last = time.time()
            print("  ...просмотрено файлов: %d, PDF найдено: %d" % (checked, len(pdfs)))
            sys.stdout.flush()
    print("просмотрено файлов: %d | PDF всего: %d | время обхода: %.1f с" % (checked, len(pdfs), time.time() - t0))

    near, orphan = 0, []
    for dirpath, n in pdfs:
        base = n[:-4]
        m = find_model_near(dirpath, base)
        if m:
            near += 1
        else:
            orphan.append((dirpath, n, base))

    print("PDF рядом с моделью: %d | PDF БЕЗ модели рядом: %d" % (near, len(orphan)))
    if not orphan:
        return
    keys = {b.lower() for _, _, b in orphan}
    print("справка по домашнему индексу для %d имён..." % len(keys))
    sys.stdout.flush()
    db = db_lookup(keys)

    trash = None
    if apply_trash:
        import datetime as _dt
        trash = os.path.join(HERE, "_trash", _dt.datetime.now().strftime("%Y-%m-%d_%H%M") + "_nomodel")
        os.makedirs(trash, exist_ok=True)
        print("убираю PDF без модели в: %s" % trash)

    print("=" * 118)
    print("  %-10s %-26s %-32s %s" % ("ТИП", "ПДФ", "ПАПКА", "ГДЕ МОДЕЛЬ (если нашлась)"))
    print("-" * 118)
    moved = 0
    for i, (dirpath, n, base) in enumerate(orphan):
        rows = db.get(base.lower())
        if rows:
            typ = "МОДЕЛЬ НЕ ТУТ"
            where = "; ".join(sorted({os.path.dirname(p) for p in rows})[:2])
        else:
            typ = "ДОКУМЕНТАЦИЯ"
            where = "модели нет ни рядом, ни в индексе (каталог/руководство/скан)"
        print("  %-10s %-26s %-32s %s" % (typ, _short(n, 26), _short(dirpath, 32), where[:60]))
        if apply_trash and not rows:
            # перемещаем только НАСТОЯЩИХ сирот (документация);
            # PDF, чья модель есть в другой папке, не трогаем — сначала перевыпустить рядом
            try:
                import shutil
                src = os.path.join(dirpath, n)
                dst = os.path.join(trash, n)
                k = 1
                while os.path.exists(dst):
                    dst = os.path.join(trash, "%s_%d%s" % (os.path.splitext(n)[0], k, os.path.splitext(n)[1])); k += 1
                shutil.move(src, dst)
                moved += 1
            except Exception as e:
                print("        ! не удалось переместить: %s" % e)
        elif apply_trash and rows:
            print("        (не трогаю: модель есть в другой папке — сначала «СОЗДАТЬ/ОБНОВИТЬ ПДФ»)" if i == 0 else "")
        if i + 1 >= limit:
            print("  ...обрезано по лимиту %d из %d" % (limit, len(orphan)))
            break
    print("-" * 118)
    inidx = sum(1 for _, _, b in orphan if db.get(b.lower()))
    print("  МОДЕЛЬ НЕ ТУТ — модель есть, но в другой папке (перевыпустить рядом)")
    print("  ДОКУМЕНТАЦИЯ  — это каталоги/руководства, для дома НОРМА (галочка удаления уберёт и их!)")
    if moved:
        print("=" * 118)
        print("УБРАНО в %s — %d файл(ов)" % (trash, moved))
    print("ИТОГО без модели рядом: %d (модель в другой папке: %d, документация: %d)"
          % (len(orphan), inidx, len(orphan) - inidx))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    lim = 200
    if "--limit" in sys.argv:
        lim = int(sys.argv[sys.argv.index("--limit") + 1])
    scan(sys.argv[1], lim, "--quiet" in sys.argv, "--apply" in sys.argv)