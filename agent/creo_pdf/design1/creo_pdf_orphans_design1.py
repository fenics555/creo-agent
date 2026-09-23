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
DB_AGENT = r"D:\AI\tools\agent\data\agent.sqlite"
DB_HARVEST = r"D:\AI\tools\agent\data\harvest.db"


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
    for db, table in ((DB_HARVEST, "models_raw"), (DB_AGENT, "models")):
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


def scan(root, limit=200, quiet=False):
    t0 = time.time()
    pdfs, checked = [], 0
    for dirpath, dirnames, filenames in os.walk(root):
        for n in filenames:
            if n.lower().endswith(".pdf"):
                pdfs.append((dirpath, n))
            checked += 1
            if checked % 2000 == 0 and not quiet:
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
    print("ищу %d имён в домашнем индексе..." % len(keys))
    db = db_lookup(keys)
    print("-" * 100)
    shown = 0
    for dirpath, n, base in orphan:
        rows = db.get(base.lower())
        if rows:
            where = "; ".join(sorted({os.path.dirname(p) for p in rows})[:3])
            state = "МОДЕЛЬ В ДРУГОЙ ПАПКЕ: " + where
        else:
            state = "модели нет и в индексе (PDF-сирота: каталог/скан/чужой файл)"
        print("НЕ РЯДОМ  %s" % os.path.join(dirpath, n))
        print("          %s" % state)
        shown += 1
        if shown >= limit:
            print("  ... (обрезано по лимиту %d из %d)" % (limit, len(orphan)))
            break
    print("-" * 100)
    print("ИТОГО без модели рядом: %d (в индексе нашлись: %d, сироты: %d)"
          % (len(orphan), sum(1 for _, _, b in orphan if db.get(b.lower())), sum(1 for _, _, b in orphan if not db.get(b.lower()))))


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
    scan(sys.argv[1], lim, "--quiet" in sys.argv)