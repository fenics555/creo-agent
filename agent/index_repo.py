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
# 04.10.2026 (аудит настроек): `chunk_size` и `chunk_overlap` были объявлены в панели настроек,
# но нарезка шла жёсткой константой CHUNK_MAX — обе были обещанием впустую. Теперь размер и
# перекрытие берутся из них; границы проверяются, мусорное значение не роняет индексацию.
DB = core.db()


def _chunk_max() -> int:
    """Размер чанка в символах (настройка `chunk_size`). Вне диапазона — безопасные 1800."""
    try:
        import settings as _st
        v = int(_st.get("chunk_size", 0) or 0)
    except Exception:
        v = 0
    return v if 200 <= v <= 20000 else 1800


def _chunk_overlap() -> int:
    """Перекрытие чанков в символах (настройка `chunk_overlap`), не больше половины чанка."""
    try:
        import settings as _st
        v = int(_st.get("chunk_overlap", 0) or 0)
    except Exception:
        v = 0
    return max(0, min(v, _chunk_max() // 2))

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
    """Нарезка на чанки по НАСТРОЙКАМ размера и перекрытия (04.10.2026, аудит настроек).
    Перекрытие нужно, чтобы фраза на стыке двух чанков не терялась из индекса."""
    cmax = _chunk_max()
    ov = _chunk_overlap()
    chunks = []
    while len(text) > cmax:
        split = text.rfind("\n", 0, cmax)
        if split == -1 or split < ov:
            split = cmax
        chunks.append(text[:split])
        rest = text[split - ov:] if ov else text[split:]
        text = rest.lstrip("\n") if ov else rest.lstrip()
        if not text:
            break
    if text:
        chunks.append(text)
    return chunks

def run(keep=False):
    log("индексация начата: root=%s" % ROOT)
    # ЖИВАЯ НАХОДКА 03.10.2026 (аудит data\, Д13): таблица chunks заполнялась БЕЗ очистки,
    # поэтому каждый повторный запуск ДОБАВЛЯЛ копии. Доказательство на старом бэкапе:
    # 1 330 971 чанков при 37 372 уникальных файлах — в среднем 35,6 копии на файл
    # (максимум 1016), и именно из-за этого база разрослась до 6,38 ГБ.
    # Теперь индекс ПЕРЕСОБИРАЕТСЯ начисто: keep=True — дописать к существующему.
    try:
        if keep:
            n_old = DB.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
            log("режим дописывания: в базе уже %d чанков" % n_old)
        else:
            DB.execute("DELETE FROM chunks")
            DB.commit()
            log("индекс очищен перед сборкой (режим пересборки)")
    except Exception as e:
        log("не смог очистить chunks: %s" % e)
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
    # --keep — дописать к существующему индексу (по умолчанию — пересборка начисто, Д13)
    run(keep="--keep" in sys.argv)
