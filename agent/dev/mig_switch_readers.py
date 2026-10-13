# -*- coding: utf-8 -*-
r"""mig_switch_readers — переключение читателей свода на схему svod (Волна 1.2, шаг 2).

Детерминированно заменяет запросы свода `FROM <таблица>` -> `FROM svod.<таблица>` в файлах,
которые читают общую agent.sqlite через core.db() (там уже приаттачен свод как svod).
Писатель fts (scanner.index_all) тоже переводится на svod.fts_index — свод пересобираем.

Каждая замена проверяется: если old не найден в файле — ОШИБКА, файл не трогается.
После замен каждый файл компилируется (py_compile). Запуск: mig_switch_readers.py
"""
import py_compile
import sys
from pathlib import Path

AGENT = Path(r"D:\AI\tools\agent")

# (относит. путь, old, new)  — old должен встречаться >=1 раза; заменяются ВСЕ вхождения.
EDITS = [
    ("db_tools.py", "SELECT COUNT(*), MAX(mtime) FROM files", "SELECT COUNT(*), MAX(mtime) FROM svod.files"),
    ("db_tools.py", "SELECT COUNT(*) FROM fts_index", "SELECT COUNT(*) FROM svod.fts_index"),
    ("find_tools.py", "SELECT name, ext, path FROM models ", "SELECT name, ext, path FROM svod.models "),
    ("find_tools.py", "SELECT ext, COUNT(*) FROM models GROUP BY ext", "SELECT ext, COUNT(*) FROM svod.models GROUP BY ext"),
    ("http_handlers.py", "SELECT child FROM bom WHERE parent LIKE ?", "SELECT child FROM svod.bom WHERE parent LIKE ?"),
    ("http_handlers.py", "SELECT child FROM links WHERE parent LIKE ?", "SELECT child FROM svod.links WHERE parent LIKE ?"),
    ("http_handlers.py", "SELECT path, mtime FROM files", "SELECT path, mtime FROM svod.files"),
    ("nightly_tools.py", "SELECT COUNT(*) FROM files", "SELECT COUNT(*) FROM svod.files"),
    ("nightly_tools.py", "SELECT COUNT(*) FROM fts_index", "SELECT COUNT(*) FROM svod.fts_index"),
    ("pdf_tools.py", "FROM files WHERE", "FROM svod.files WHERE"),
    ("similar_tools.py", "FROM models m JOIN model_embs e ON e.name=m.name", "FROM svod.models m JOIN svod.model_embs e ON e.name=m.name"),
    ("similar_tools.py", "SELECT emb FROM model_embs WHERE name=?", "SELECT emb FROM svod.model_embs WHERE name=?"),
    ("timeline_tools.py", "FROM files WHERE", "FROM svod.files WHERE"),
    ("vision_audit.py", "SELECT path, mtime FROM files", "SELECT path, mtime FROM svod.files"),
    # scanner: init_db_schema (схема) — чтобы после DROP свод не пересоздавался в main
    ("scanner.py", "CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY", "CREATE TABLE IF NOT EXISTS svod.files(path TEXT PRIMARY KEY"),
    ("scanner.py", "CREATE TABLE IF NOT EXISTS models(name TEXT, ext TEXT, path TEXT)", "CREATE TABLE IF NOT EXISTS svod.models(name TEXT, ext TEXT, path TEXT)"),
    # scanner: читатель-дубли моделей + ПИСАТЕЛЬ fts (index_all) + читатель fts (search)
    ("scanner.py", "SELECT name, COUNT(*) FROM models GROUP BY name HAVING COUNT(*) > 1", "SELECT name, COUNT(*) FROM svod.models GROUP BY name HAVING COUNT(*) > 1"),
    ("scanner.py", "CREATE VIRTUAL TABLE IF NOT EXISTS fts_index USING fts5", "CREATE VIRTUAL TABLE IF NOT EXISTS svod.fts_index USING fts5"),
    ("scanner.py", "DELETE FROM fts_index", "DELETE FROM svod.fts_index"),
    ("scanner.py", "INSERT INTO fts_index(path, content) VALUES(?,?)", "INSERT INTO svod.fts_index(path, content) VALUES(?,?)"),
    ("scanner.py", "SELECT path, content FROM fts_index WHERE fts_index MATCH ? ", "SELECT path, content FROM svod.fts_index WHERE svod.fts_index MATCH ? "),
    ("scanner.py", "SELECT path, content FROM fts_index WHERE content LIKE ? LIMIT ?", "SELECT path, content FROM svod.fts_index WHERE content LIKE ? LIMIT ?"),
    # navigator (GUI): bom и models
    ("navigator/navigator.py", "SELECT child, qty FROM bom WHERE LOWER(parent)=? LIMIT ?", "SELECT child, qty FROM svod.bom WHERE LOWER(parent)=? LIMIT ?"),
    ("navigator/navigator.py", "SELECT path FROM models WHERE LOWER(name)=? LIMIT 1", "SELECT path FROM svod.models WHERE LOWER(name)=? LIMIT 1"),
]


def main():
    fails = []
    touched = {}
    for rel, old, new in EDITS:
        p = AGENT / rel
        if not p.exists():
            fails.append("%s: файла нет" % rel)
            continue
        src = p.read_text(encoding="utf-8")
        if old not in src:
            fails.append("%s: якорь не найден: %r" % (rel, old[:50]))
            continue
        n = src.count(old)
        src = src.replace(old, new)
        p.write_text(src, encoding="utf-8")
        touched[rel] = touched.get(rel, 0) + n
        print("OK %-24s x%d  %s" % (rel, n, old[:46]))
    # Компиляция всех затронутых
    print("--- py_compile ---")
    for rel in touched:
        try:
            py_compile.compile(str(AGENT / rel), doraise=True)
            print("compile OK %s" % rel)
        except Exception as e:
            fails.append("%s: py_compile: %s" % (rel, e))
    print("--- итог ---")
    for rel, n in sorted(touched.items()):
        print("  %s: замен %d" % (rel, n))
    if fails:
        print("ОШИБКИ (%d):" % len(fails))
        for f in fails:
            print("  " + f)
        return 1
    print("ВСЕ ЗАМЕНЫ ПРИМЕНЕНЫ, КОМПИЛЯЦИЯ ЧИСТА")
    return 0


if __name__ == "__main__":
    sys.exit(main())
