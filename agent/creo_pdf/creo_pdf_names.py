# -*- coding: utf-8 -*-
"""Индекс БАЗОВЫХ имён моделей дома для PDF-рутины (класс Р, без Creo, только чтение баз).
Пишет D:\\AI\\log\\creo_pdf\\model_names.txt — по строке на имя (нижний регистр, без расширения/версии).
Нужен рутине, чтобы отличать ЧЕРТЁЖ-СИРОТУ (модели нет нигде) от настоящей ошибки открытия.
"""
import os
import re
import sqlite3
import sys

LOG_DIR = r"D:\AI\log\creo_pdf"
OUT = os.path.join(LOG_DIR, "model_names.txt")
DB_AGENT = r"D:\AI\tools\agent\data\agent.sqlite"
DB_HARVEST = r"D:\AI\tools\agent\data\harvest.db"


def base_of(fn):
    return re.sub(r"\.(prt|asm)(\.\d+)?$", "", str(fn).lower(), flags=re.I).strip()


def main(argv):
    quiet = "--quiet" in argv
    names = set()
    for db, table in ((DB_AGENT, "models"), (DB_HARVEST, "models_raw")):
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