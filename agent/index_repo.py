# -*- coding: utf-8 -*-
"""Индексатор репозитория: чанчит текстовые файлы, считает эмбеддинги, пишет в chunks.
Запуск: cd D:\\AI\\tools\\agent && python data\\tmp\\index_repo.py
Лог пишется в data\\tmp\\index_repo.log."""
import sys, os, json, time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import core
import numpy as np

ROOT = Path(r"D:\AI\repo")
CHUNK_MAX = 1800  # символов на чанк (примерно 400-500 токенов)
DB = core.db()

LOG_PATH = os.path.join(os.path.dirname(__file__), "index_repo.log")

def log(msg):
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write("[%s] %s\n" % (time.strftime("%H:%M:%S"), msg))

def is_text(path):
    ext = path.suffix.lower()
    return ext in {".md", ".txt", ".py", ".json", ".yaml", ".yml", ".xml",
                   ".html", ".css", ".js", ".csv", ".eprim", ".part", ".asix",
                   ".jxl", ".tfwx", ".tkb"}

def chunk_text(text):
    chunks = []
    while len(text) > CHUNK_MAX:
        split = text.rfind("\n", 0, CHUNK_MAX)
        if split == -1:
            split = CHUNK_MAX
        chunks.append(text[:split])
        text = text[split:].lstrip()
    if text:
        chunks.append(text)
    return chunks

def run():
    log("индексация начата: root=%s" % ROOT)
    files_indexed = 0
    chunks_created = 0
    errors = 0

    for p in sorted(ROOT.rglob("*")):
        if not p.is_file():
            continue
        if not is_text(p):
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            log("ошибка чтения %s: %s" % (p.name, e))
            errors += 1
            continue

        if not content.strip():
            continue

        for i, chunk in enumerate(chunk_text(content)):
            try:
                emb = core.embed(chunk)
                if not emb:
                    log("пустой эмбеддинг для %s (чанк %d)" % (p.name, i))
                    continue
                DB.execute("INSERT INTO chunks(path, text, emb) VALUES(?,?,?)",
                          (str(p), chunk[:300] + ("..." if len(chunk) > 300 else ""),
                           np.array(emb, np.float32).tobytes()))
                chunks_created += 1
            except Exception as e:
                log("ошибка эмбеддинга %s (чанк %d): %s" % (p.name, i, e))
                errors += 1
                continue
        files_indexed += 1
        if files_indexed % 10 == 0:
            log("прогресс: %d файлов, %d чанков" % (files_indexed, chunks_created))

    log("индексация завершена: файлов=%d, чанков=%d, ошибок=%d" %
        (files_indexed, chunks_created, errors))

if __name__ == "__main__":
    run()
