# -*- coding: utf-8 -*-
r"""mig_brain_summary — сборка сводной БД из общей (Волна 1.2 плана, шаг 1.2).

Что делает: читает общую agent.sqlite ТОЛЬКО на чтение (mode=ro) и собирает рядом
data\summary.sqlite — свод (files, models, model_embs, bom, links, chunks + fts_index).
Общая при этом НЕ меняется и НЕ удаляется: это сборка производного свода (канон:
свод пересобираем, потеря свода не критична). Переключение читателей свода на
summary.sqlite — отдельный шаг (по одному файлу), этим скриптом НЕ делается.

DDL таблиц берётся из sqlite_master общей (source of truth), не хардкодится.
fts_index — виртуальная fts5: в своде создаётся та же таблица, данные льются через
INSERT INTO fts_index(path, content) SELECT ... — FTS5 сам строит индексы.

Запуск:  mig_brain_summary.py            (dry-run: только план + COUNT, файл не пишется)
         mig_brain_summary.py --apply     (создать/перезаписать data\summary.sqlite)
Код возврата: 0 — окно · 2 — общей нет.
"""
import argparse
import hashlib
import os
import sqlite3
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
AGENT = HERE.parent                              # tools\agent
DATA = AGENT / "data"
MAIN_DB = DATA / "agent.sqlite"
SUM_DB = DATA / "summary.sqlite"

# Сводные таблицы общей (по инвентаризации db_profile, Волна 1.1): данные, а не мозг.
SVOD = ["files", "models", "model_embs", "bom", "links", "chunks"]
FTS = "fts_index"


def ro(path):
    """Подключение только на чтение (не создаёт и не блокирует запись)."""
    uri = "file:%s?mode=ro" % str(path).replace("\\", "/")
    return sqlite3.connect(uri, uri=True)


def ddl_of(sc, name):
    """CREATE-оператор таблицы из src.sqlite_master (None если таблицы нет)."""
    row = sc.execute("SELECT sql FROM src.sqlite_master WHERE name=? AND sql IS NOT NULL", (name,)).fetchone()
    return row[0] if row else None


def count_of(sc, schema, name):
    """Число строк таблицы в схеме schema (main|src); -1 если нет/ошибка."""
    try:
        return sc.execute('SELECT COUNT(*) FROM %s."%s"' % (schema, name)).fetchone()[0]
    except Exception:
        return -1


def sha8(path):
    h = hashlib.sha256()
    with open(str(path), "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()[:8]


def build(sc, log):
    """Перенос свода из src (общая) в main (свод) в ОДНОМ соединении через ATTACH.

    Возвращает {таблица: строк в своде после переноса}. DDL и данные — из src,
    запись — в main; COUNT сверяется с src (контроль полноты).
    """
    moved = {}
    for name in SVOD:
        ddl = ddl_of(sc, name)
        if ddl is None:
            log.append("  %-14s нет в общей — пропуск" % name)
            continue
        src_n = count_of(sc, "src", name)
        sc.execute('DROP TABLE IF EXISTS main."%s"' % name)
        sc.execute(ddl)
        sc.execute('INSERT INTO main."%s" SELECT * FROM src."%s"' % (name, name))
        got = count_of(sc, "main", name)
        if got != src_n:
            raise RuntimeError("контроль: %s перенесено %d из %d" % (name, got, src_n))
        moved[name] = got
        log.append("  %-14s перенесено строк: %d (контроль src=%d совпал)" % (name, got, src_n))
    # FTS5: та же виртуальная таблица, данные через INSERT (FTS5 строит индексы сам).
    fts_ddl = ddl_of(sc, FTS)
    if fts_ddl:
        src_n = count_of(sc, "src", FTS)
        sc.execute('DROP TABLE IF EXISTS main."%s"' % FTS)
        sc.execute(fts_ddl)
        sc.execute("INSERT INTO main.%s(path, content) SELECT path, content FROM src.%s" % (FTS, FTS))
        got = count_of(sc, "main", FTS)
        if got != src_n:
            raise RuntimeError("контроль: fts перенесено %d из %d" % (got, src_n))
        moved[FTS] = got
        log.append("  %-14s перенесено строк: %d (индекс перестроен FTS5, контроль совпал)" % (FTS, got))
    return moved


def main(argv):
    ap = argparse.ArgumentParser(description="Сборка сводной БД из общей (dry-run по умолчанию)")
    ap.add_argument("--apply", action="store_true", help="создать/перезаписать summary.sqlite")
    a = ap.parse_args(argv)
    log = []

    if not MAIN_DB.exists():
        print("нет общей БД: %s" % MAIN_DB)
        return 2

    log.append("=== MIG BRAIN/SUMMARY: %s ===" % MAIN_DB)
    log.append("общая (только чтение): %s, %.1f МБ"
               % (MAIN_DB, os.path.getsize(str(MAIN_DB)) / 1048576))
    log.append("сводная цель: %s" % SUM_DB)
    log.append("план-таблицы свода: %s + %s" % (", ".join(SVOD), FTS))

    try:
        if not a.apply:
            log.append("РЕЖИМ: dry-run — файл не пишется. План:")
            mc = ro(MAIN_DB)
            try:
                for name in SVOD + [FTS]:
                    row = mc.execute(
                        "SELECT COUNT(*) FROM sqlite_master WHERE name=? AND sql IS NOT NULL", (name,)
                    ).fetchone()
                    if not row:
                        log.append("  %-14s нет в общей — пропуск" % name)
                        continue
                    log.append("  %-14s строк в общей: %d"
                               % (name, count_of(mc, "main", name)))
            finally:
                mc.close()
            log.append("для сборки: --apply")
        else:
            log.append("РЕЖИМ: apply — сборка %s" % SUM_DB)
            tmp = SUM_DB.with_suffix(".sqlite.tmp")
            if tmp.exists():
                tmp.unlink()
            src_uri = "file:%s?mode=ro" % str(MAIN_DB).replace("\\", "/")
            tmp_uri = "file:%s" % str(tmp).replace("\\", "/")
            sc = sqlite3.connect(tmp_uri, uri=True)
            try:
                sc.execute("ATTACH DATABASE '%s' AS src" % src_uri)
                with sc:
                    build(sc, log)
                sc.execute("DETACH DATABASE src")
                sc.close()
                os.replace(str(tmp), str(SUM_DB))
            except Exception:
                try:
                    sc.close()
                finally:
                    for junk in (tmp, tmp.with_name(tmp.name + "-wal"), tmp.with_name(tmp.name + "-shm")):
                        if junk.exists():
                            junk.unlink()
                raise
            log.append("готово: %s, %.1f МБ, sha8=%s"
                       % (SUM_DB, os.path.getsize(str(SUM_DB)) / 1048576, sha8(SUM_DB)))
            log.append("ПРИМЕЧАНИЕ: общая НЕ менялась. Переключение читателей свода на")
            log.append("summary.sqlite — отдельный шаг по одному файлу (спека Волны 1, §3.1).")
    finally:
        pass

    out = "\n".join(log)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
