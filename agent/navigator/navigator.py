# -*- coding: utf-8 -*-
"""navigator — движок «НАВИГАТОРА по дому» (класс Р, без Creo).

Что умеет:
  find(query)          — найти модели/сборки/чертежи по имени и по пути (несколько вариантов написания);
  bom(model)           — деталировка: состав сборки из индекса дома (таблица `bom`, только чтение);
  pdf_for(path_or_name)— где лежит PDF этой модели/чертежа (рядом или по таблице `pairs`);
  render_pdf(path, w)  — картинка первой страницы PDF (PyMuPDF) для показа в окне.

Базы дома — ТОЛЬКО ЧТЕНИЕ: `data\\agent.sqlite` (`models`, `bom`, `usage`) и `data\\harvest.db`
(`models_raw`, `pairs`). Своих таблиц движок не создаёт.
"""
import os
import re
import sqlite3
from pathlib import Path

AG_DB = Path(r"D:\AI\tools\agent\data\agent.sqlite")
HV_DB = Path(r"D:\AI\tools\agent\data\harvest.db")
CREO_RE = re.compile(r"\.(prt|asm|drw|frm|sec|lay)(\.\d+)?$", re.I)


def base_of(name):
    """`деталь.prt.3` / `деталь.prt` -> `деталь`."""
    return CREO_RE.sub("", os.path.basename(str(name)))


def kind_of(name):
    m = re.search(r"\.(prt|asm|drw|frm|sec|lay)(\.\d+)?$", str(name), re.I)
    if not m:
        return "?"
    return {"prt": "деталь", "asm": "сборка", "drw": "чертёж", "frm": "форматка",
            "sec": "сечение", "lay": "слой"}[m.group(1).lower()]


def variants(q):
    """Варианты написания запроса: как есть + латиница<->кириллица и «ё/е».
    Живой факт 23.09.2026: «турновер» в индексе выглядит как `turn`/`турн`/`поворот» — ищем все."""
    q = (q or "").strip().lower().replace("ё", "е")
    out = {q}
    pairs = [("turn", "турн"), ("over", "овер"), ("turnover", "турновер"), ("turn", "поворот"),
             ("t", "т"), ("o", "о"), ("u", "у"), ("r", "р")]
    for lat, cyr in pairs:
        if lat in q:
            out.add(q.replace(lat, cyr))
        if cyr in q:
            out.add(q.replace(cyr, lat))
    out.add(q.replace("turnover", "turn").replace("турновер", "турн"))
    return [v for v in out if v]


def _connect(db, ro=True):
    return sqlite3.connect(("file:%s?mode=ro" % db) if ro else str(db), uri=ro)


def find(query, limit=300, only_asm=False):
    """Поиск по имени И по пути в двух базах дома. Возвращает список словарей:
    {name, base, path, folder, kind, source, ext}."""
    res, seen = [], set()
    for v in variants(query):
        like = "%" + v + "%"
        for db, table, src in ((AG_DB, "models", "index"), (HV_DB, "models_raw", "harvest")):
            try:
                c = _connect(db)
            except Exception:
                continue
            try:
                for name, ext, path in c.execute(
                        "SELECT name, ext, path FROM %s WHERE LOWER(name) LIKE ? OR LOWER(path) LIKE ? LIMIT ?"
                        % table, (like, like, limit)):
                    if only_asm and (ext or "").lower() != "asm":
                        continue
                    key = (os.path.basename(path or "").lower(), (path or "").lower())
                    if key in seen:
                        continue
                    seen.add(key)
                    res.append({"name": name, "base": base_of(name), "path": path,
                                "folder": os.path.dirname(path or ""), "ext": (ext or "").lower(),
                                "kind": kind_of(path or name), "source": src})
            except Exception:
                pass
            finally:
                c.close()
    res.sort(key=lambda r: (0 if r["kind"] == "сборка" else 1 if r["kind"] == "деталь" else 2, r["name"].lower()))
    return res[:limit]


def bom(model, depth=2, limit=2000):
    """Деталировка: состав сборки из индекса дома (таблица `bom`, ТОЛЬКО ЧТЕНИЕ).
    Возвращает список {level, name, base, qty, path, kind, has_pdf, pdf}. Пусто — состава в индексе нет."""
    root = os.path.basename(str(model)).lower()
    if "." not in root:
        root = root + ".asm.1"
    c = _connect(AG_DB)
    out, seen = [], set()

    def children(parent_name, level):
        if level > depth or len(out) >= limit:
            return
        rows = c.execute("SELECT child, qty FROM bom WHERE LOWER(parent)=? LIMIT ?",
                         (parent_name, limit)).fetchall()
        for i, (child, qty) in enumerate(rows):
            if len(out) >= limit:
                return
            if (child, level) in seen:
                continue
            seen.add((child, level))
            p = _path_of(c, child)
            pdf = pdf_for(p or child, c)
            out.append({"level": level, "name": child, "base": base_of(child), "qty": qty or 1,
                        "path": p, "kind": kind_of(child), "has_pdf": bool(pdf), "pdf": pdf})
            if kind_of(child) == "сборка":
                children(child.lower(), level + 1)

    children(root, 1)
    c.close()
    return out


def _path_of(c, name):
    """Где лежит файл с таким именем (ищем по индексу: сначала agent.sqlite, потом harvest.db)."""
    n = os.path.basename(str(name))
    try:
        r = c.execute("SELECT path FROM models WHERE LOWER(name)=? LIMIT 1", (n.lower(),)).fetchone()
        if r:
            return r[0]
    except Exception:
        pass
    for db, table in ((AG_DB, "models"), (HV_DB, "models_raw")):
        try:
            d = _connect(db)
            try:
                r = d.execute("SELECT path FROM %s WHERE LOWER(name)=? LIMIT 1" % table, (n.lower(),)).fetchone()
                if r:
                    return r[0]
            finally:
                d.close()
        except Exception:
            continue
    return None


def pdf_for(path_or_name, conn=None):
    """PDF модели/чертежа: сначала рядом («имя.pdf»), потом по таблице `pairs` (модель -> pdf)."""
    p = str(path_or_name or "")
    if not p:
        return None
    stem = re.sub(r"\.\d+$", "", p)                     # убираем версию Creo
    stem = re.sub(r"\.(prt|asm|drw|frm|sec|lay)$", "", stem, flags=re.I)
    cand = Path(stem + ".pdf")
    if cand.exists():
        return str(cand)
    name = os.path.basename(p).lower()
    bases = [os.path.basename(p).lower(), os.path.basename(stem).lower(),
             base_of(p).lower()]
    try:
        c = conn or _connect(HV_DB)
        for b in bases:
            for like in (b, b + ".%", "%\\" + b + ".drw.%", "%\\" + b + ".prt.%", "%\\" + b + ".asm.%"):
                r = c.execute("SELECT pdf_path FROM pairs WHERE LOWER(model) LIKE ? LIMIT 1", (like,)).fetchone()
                if r:
                    return r[0]
    except Exception:
        return None
    finally:
        if conn is None:
            try:
                c.close()
            except Exception:
                pass
    return None


def pdf_status(pdf_path):
    """Свежесть пары из harvest.db (`актуален`/`устарел`) — если запись есть."""
    if not pdf_path:
        return ""
    try:
        c = _connect(HV_DB)
        r = c.execute("SELECT freshness FROM pairs WHERE LOWER(pdf_path)=? LIMIT 1",
                      (str(pdf_path).lower(),)).fetchone()
        c.close()
        return r[0] if r else ""
    except Exception:
        return ""


def render_pdf(pdf_path, width=520, page=0):
    """Первая страница PDF как PNG-байты (PyMuPDF) — для показа в окне.
    Возвращает (bytes, (ширина, высота, всего_страниц)) или (None, причина)."""
    try:
        import pymupdf as fitz            # 1.28.2 в системе; старый импорт fitz ругается deprecation
    except Exception:
        try:
            import fitz
        except Exception as e:
            return None, "нет PyMuPDF: %s" % e
    try:
        doc = fitz.open(str(pdf_path))
        if page >= doc.page_count:
            page = 0
        pg = doc.load_page(page)
        k = width / max(1.0, pg.rect.width)
        pix = pg.get_pixmap(matrix=fitz.Matrix(k, k))
        data = pix.tobytes("png")
        size = (pix.width, pix.height, doc.page_count)
        doc.close()
        return data, size
    except Exception as e:
        return None, "не отрисовать PDF: %s" % e


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(0)
    cmd = sys.argv[1]
    if cmd == "find":
        for r in find(sys.argv[2] if len(sys.argv) > 2 else "", limit=25):
            print("%-10s %-38s %s" % (r["kind"], r["name"], r["folder"]))
    elif cmd == "bom":
        rows = bom(sys.argv[2], depth=int(sys.argv[3]) if len(sys.argv) > 3 else 2)
        print("позиций: %d" % len(rows))
        for r in rows[:40]:
            print("%s%-8s %-34s qty=%-4s pdf=%s" % ("  " * (r["level"] - 1), r["kind"], r["name"],
                                                    r["qty"], "да" if r["has_pdf"] else "нет"))
    elif cmd == "pdf":
        p = pdf_for(sys.argv[2])
        print("PDF: %s (%s)" % (p, pdf_status(p) or "нет в pairs"))
        if p:
            data, info = render_pdf(p, 400)
            print("страница отрисована: %s" % (info,))