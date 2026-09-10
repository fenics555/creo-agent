# -*- coding: utf-8 -*-
"""АГЕНТ v12 — БЛОК PDF (pdf_tools.py)
PDF-глаза: свежесть одноимённых pdf/drw в той же папке (таблица files),
миниатюры листов (fitz, кэш data/pdfcache), перепечать чертежа через CREOSON.
Свежесть: pdf mtime >= drw mtime → «актуален», иначе «УСТАРЕЛ»; prt/asm не учитываются.
"""
import os, re, sqlite3
from pathlib import Path
import datetime

import settings
from core import log

try:
    import fitz
    HAS_FITZ = True
except Exception:
    HAS_FITZ = False

AG = Path(__file__).parent
CACHE_DIR = AG / "data" / "pdfcache"
IMG_DPI = 80  # миниатюра читаема, кэш не пухнет


def _ts(m):
    return datetime.datetime.fromtimestamp(m or 0).strftime("%y-%m-%d %H:%M:%S") if m else "нет"


def _lookup(name):
    """По стему имени из files: одноимённые .pdf и .drw в той же папке.
    Возвращает (pdf_path, drw_path, pdf_mtime, drw_mtime)."""
    stem = name.lower()
    c = sqlite3.connect(str(AG / "agent.sqlite"))
    try:
        rows = c.execute("SELECT path, mtime FROM files").fetchall()
    finally:
        c.close()
    pdf_m = drw_m = None
    pdf_p = drw_p = None
    for p, m in rows:
        base = os.path.basename(str(p))
        m2 = re.match(r"^(.+)\.(drw|pdf)(?:\.\d+)?$", base, re.I)
        if not m2 or m2.group(1).lower() != stem:
            continue
        ext = m2.group(2).lower()
        pl = str(p).lower()
        if not os.path.exists(str(p)):
            continue
        if ext == ".pdf":
            if pdf_m is None or (m or 0) > pdf_m:
                pdf_m, pdf_p = m, pl
        else:
            if drw_m is None or (m or 0) > drw_m:
                drw_m, drw_p = m, pl
    return pdf_p, drw_p, pdf_m, drw_m
