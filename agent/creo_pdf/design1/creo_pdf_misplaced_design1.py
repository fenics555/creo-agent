# -*- coding: utf-8 -*-
r"""PDF НЕ В СВОЕЙ ПАПКЕ (ошибка вывода): одноимённый ЧЕРТЁЖ лежит в одной папке, а его PDF — в другой.

Разделяет три разных случая:
  • СМЕЩЁН   — PDF есть, но НЕ рядом со своим чертежом (ошибка конструктора; надо перевыпустить рядом, лишний убрать);
  • ЛИШНИЙ   — PDF есть и рядом, И ещё в другой папке (дубль);
  • ДОКУМЕНТАЦИЯ — PDF без одноимённого чертежа нигде (каталоги, руководства...) — это НОРМА, не ошибка.

Запуск:
    python creo_pdf_misplaced.py <папка> [--limit 200] [--doc]     # только отчёт
    python creo_pdf_misplaced.py <папка> --apply                   # убрать найденные в _trash
"""
import os, re, shutil, sys, time, datetime

MODEL_RX = re.compile(r"\.(drw|prt|asm|frm)(\.\d+)?$", re.I)
HERE = os.path.dirname(os.path.abspath(__file__))


def walk_tree(root, quiet=False):
    """Возвращает (pdfs, models, files): base_lower -> список (папка, имя[, тип])"""
    pdfs, models, files = {}, {}, 0
    for dirpath, dirnames, filenames in os.walk(root):
        for n in filenames:
            files += 1
            low = n.lower()
            if low.endswith(".pdf"):
                pdfs.setdefault(low[:-4], []).append((dirpath, n))
            else:
                m = MODEL_RX.search(n)
                if m:
                    models.setdefault(n[:m.start()].lower(), []).append((dirpath, n, m.group(1).lower()))
        if not quiet and files and files % 2000 == 0:
            print("  ...файлов: %d, PDF: %d" % (files, sum(len(v) for v in pdfs.values())))
            sys.stdout.flush()
    return pdfs, models, files


def db_lookup(bases):
    """Где в доме лежит модель с таким именем (префиксный поиск по индексу агента).
    Возвращает {base: [(path, ext)]}, ext — drw/prt/asm/frm."""
    DB = ((r"D:\AI\tools\agent\data\harvest.db", "models_raw"),
          (r"D:\AI\tools\agent\data\agent.sqlite", "models"))
    out = {}
    if not bases:
        return out
    import sqlite3
    for db, table in DB:
        if not os.path.exists(db):
            continue
        try:
            c = sqlite3.connect("file:%s?mode=ro" % db.replace("\\", "/"), uri=True)
            cols = [d[1] for d in c.execute("PRAGMA table_info(%s)" % table)]
            if "name" not in cols or "path" not in cols:
                c.close(); continue
            sql = "SELECT name, path FROM %s WHERE lower(name) LIKE ? ESCAPE '\\'" % table
            for b in bases:
                if b in out:
                    continue
                like = b.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + ".%"
                try:
                    rows = c.execute(sql, (like,)).fetchall()
                except Exception:
                    continue
                hits = []
                for nm, p in rows:
                    m = MODEL_RX.search(str(nm))
                    if m:
                        hits.append((str(p), m.group(1).lower()))
                if hits:
                    out[b] = sorted(set(hits))
            c.close()
        except Exception:
            pass
    return out


def analyze(pdfs, models, db=None):
    """Группы по имени: где чертёж, какие копии PDF рядом, какие в других папках.
    Возвращает (groups, no_pdf, docs, info).
    group = (base, drw_dirs, near, away, src)  — near/away: списки (папка, имя)."""
    db = db or {}
    groups, docs, info = [], [], []
    for base, plist in sorted(pdfs.items()):
        md = models.get(base, [])
        drw_dirs = {d for d, _, e in md if e == "drw"}
        if drw_dirs:
            src = "чертёж в этой ветке"
        else:
            rows = db.get(base, [])
            drws = [p for p, e in rows if e == "drw"]
            if drws:
                drw_dirs = {os.path.dirname(p) for p in drws}
                src = "чертёж найден по индексу дома"
            else:
                mods = [(p, e) for p, e in rows if e in ("prt", "asm")]
                if mods:
                    info.append((base, plist, sorted({os.path.dirname(p) for p, _ in mods})[:2]))
                else:
                    docs.append((base, plist))
                continue
        near = sorted([p for p in plist if p[0] in drw_dirs])
        away = sorted([p for p in plist if p[0] not in drw_dirs])
        if away:
            groups.append((base, sorted(drw_dirs), near, away, src))
    no_pdf = sum(1 for b, md in models.items()
                 if any(e == "drw" for _, _, e in md) and b not in pdfs)
    return groups, no_pdf, docs, info


def _info(p):
    try:
        st = os.stat(p)
        return st.st_size, time.strftime("%d.%m.%Y %H:%M", time.localtime(st.st_mtime)), st.st_mtime
    except Exception:
        return 0, "?", 0


def main(root, limit, show_doc, apply_trash):
    t0 = time.time()
    pdfs, models, files = walk_tree(root)
    copies = sum(len(v) for v in pdfs.values())
    print("просмотрено файлов: %d | PDF-файлов: %d (уникальных имён: %d) | обход: %.1f с"
          % (files, copies, len(pdfs), time.time() - t0))
    need = [b for b in pdfs if not any(e == "drw" for _, _, e in models.get(b, []))]
    print("справка по домашнему индексу для %d имён..." % len(need)); sys.stdout.flush()
    db = db_lookup(need)
    groups, no_pdf, docs, info = analyze(pdfs, models, db)
    no_near = [g for g in groups if not g[2]]
    dups = [g for g in groups if g[2]]
    print("чертежей без PDF вообще: %d" % no_pdf)
    print("ГРУПП С КОПИЯМИ НЕ ТАМ: %d  →  вовсе нет копии рядом: %d, есть рядом + лишние копии: %d"
          % (len(groups), len(no_near), len(dups)))
    print("PDF-от-модели (не чертёж): %d | документация (норма): %d | копий в этих группах: %d"
          % (len(info), len(docs), sum(len(g[2]) + len(g[3]) for g in groups)))

    trash = None
    if apply_trash and dups:
        stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
        trash = os.path.join(HERE, "_trash", stamp)
        os.makedirs(trash, exist_ok=True)
        print("лишние копии убираю в: %s" % trash)
    if apply_trash and no_near:
        print("! у %d групп НЕТ копии рядом с чертежом — не трогаю их: сначала «СОЗДАТЬ/ОБНОВИТЬ PDF», потом уборка" % len(no_near))

    print("-" * 110)
    for base, drw_dirs, near, away, src in groups[:limit]:
        print("%s  %s   [%s; копий: %d]" % ("НЕТ РЯДОМ" if not near else "ДУБЛЬ    ",
                                            base, src, len(near) + len(away)))
        print("        чертёж: %s" % drw_dirs[0])
        for d, n in near:
            sz, dt, _ = _info(os.path.join(d, n))
            print("        РЯДОМ    (%9d б, %s)  %s" % (sz, dt, n))
        near_max = max([_info(os.path.join(d, n))[2] for d, n in near], default=0)
        for d, n in away:
            p = os.path.join(d, n); sz, dt, mt = _info(p)
            mark = "  <-- ВНИМАНИЕ: копия СВЕЖЕЕ той, что рядом" if (near and mt > near_max) else ""
            print("        НЕ РЯДОМ (%9d б, %s)  %s%s" % (sz, dt, p, mark))
            if apply_trash and near:
                try:
                    dst = os.path.join(trash, n)
                    k = 1
                    while os.path.exists(dst):
                        dst = os.path.join(trash, "%s_%d%s" % (os.path.splitext(n)[0], k, os.path.splitext(n)[1])); k += 1
                    shutil.move(p, dst)
                    print("                 -> убран в корзину инструмента")
                except Exception as e:
                    print("                 ! не удалось убрать: %s" % e)
    if len(groups) > limit:
        print("  ...обрезано по лимиту %d из %d" % (limit, len(groups)))
    if info:
        print("-" * 110)
        print("PDF ОТ МОДЕЛИ (не чертёж; модель лежит в другой папке):")
        for base, plist, mods in info[:limit]:
            print("   %s   <- модель: %s" % (os.path.join(plist[0][0], plist[0][1]), "; ".join(mods)))
    if show_doc and docs:
        print("-" * 110)
        print("ДОКУМЕНТАЦИЯ (первые %d) — не ошибка, просто одинокие PDF:" % limit)
        for base, plist in docs[:limit]:
            print("   %s" % os.path.join(plist[0][0], plist[0][1]))
    print("-" * 110)
    if trash:
        print("УБРАНО в: %s" % trash)
    print("ИТОГО: групп с копиями не там %d (без копии рядом %d, дублей %d), PDF-от-модели %d, документации %d, чертежей без PDF %d"
          % (len(groups), len(no_near), len(dups), len(info), len(docs), no_pdf))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 200
    main(sys.argv[1], lim, "--doc" in sys.argv, "--apply" in sys.argv)