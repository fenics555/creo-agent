# -*- coding: utf-8 -*-
"""Индекс БАЗОВЫХ имён моделей дома для PDF-рутины (класс Р, без Creo, только чтение баз).
Пишет D:\\AI\\log\\creo_pdf\\model_names.txt — по строке на имя (нижний регистр, без расширения/версии).
Нужен рутине, чтобы отличать ЧЕРТЁЖ-СИРОТУ (модели нет нигде) от настоящей ошибки открытия.
"""
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import creo_pdf_env as env                                   # noqa: E402

LOG_DIR = env.find_logs_dir()
OUT = os.path.join(LOG_DIR, "model_names.txt")


def base_of(fn):
    return re.sub(r"\.(prt|asm)(\.\d+)?$", "", str(fn).lower(), flags=re.I).strip()


def main(argv):
    quiet = "--quiet" in argv
    dbs = env.find_db_files()          # [(путь, таблица)] — ищет рядом с инструментом и выше
    if not dbs:
        print("  базы моделей не найдены (ищу рядом с инструментом и в родительских папках)")
    names = set()
    for db, table in dbs:
        if not os.path.exists(db):
            continue
        try:
            c = sqlite3.connect("file:%s?mode=ro" % db.replace("\\", "/"), uri=True)
            for (n,) in c.execute("SELECT name FROM %s" % table):
                if n and re.search(r"\.(prt|asm)(\.\d+)?$", str(n).lower()):
                    b = base_of(n)
                    if b:
                        names.add(b)
            c.close()
        except Exception as e:
            print("  %s: %s" % (table, e))
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for n in sorted(names):
            f.write(n + "\n")
    if not quiet:
        print("индекс имён моделей: %d имён → %s" % (len(names), OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))