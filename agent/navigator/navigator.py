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


def find_words(query, limit=300, only_asm=False):
    """Поиск «по словам», как человек пишет: «найди сборки турноверов» — слова разбиваются,
    каждое ищется со своими вариантами написания, результат — те, где совпало больше слов.
    Это то, чего не хватало простому поиску по подстроке."""
    words = [w for w in re.split(r"[\s,;.]+", (query or "").strip().lower()) if len(w) >= 2]
    if not words:
        return []
    score = {}
    info = {}
    for w in words:
        for r in find(w, limit=limit, only_asm=only_asm):
            key = (r["name"].lower(), (r["path"] or "").lower())
            score[key] = score.get(key, 0) + 1
            info.setdefault(key, r)
    if not score:
        return []
    need = len(words)
    ranked = sorted(info.items(), key=lambda kv: (-score[kv[0]], kv[1]["name"].lower()))
    out = []
    for key, r in ranked:
        hit = score[key]
        r = dict(r)
        r["words_hit"] = hit
        r["words_all"] = need
        out.append(r)
    return out[:limit]


def bom_live(model, path=None, open_if_needed=True, cleanup=True, timeout=30):
    """Состав сборки ИЗ ЖИВОЙ СЕССИИ Creo (через CREOSON дома: `bom get_paths`).
    Возвращает (rows, ошибка): rows в том же виде, что и `bom()`, но без PDF.
    Если Creo/CREOSON недоступны — вернёт (None, «почему»)."""
    try:
        sys_path = r"D:\AI\tools\agent"
        if sys_path not in __import__("sys").path:
            __import__("sys").path.insert(0, sys_path)
        import creo_tools as CT          # живёт в папке агента
    except Exception as e:
        return None, "нет доступа к живой сессии (не найден creo_tools): %s" % e

    name = os.path.basename(str(model))
    # ЖИВОЙ ФАКТ 23.09.2026: CREOSON у `bom get_paths` НЕ принимает версию Creo в имени —
    # `d25.asm.1` даёт «Unknown Model Extension» (расширением он видит `.1`). Нужно `d25.asm`.
    name = re.sub(r"\.\d+$", "", name)
    if not re.search(r"\.(prt|asm)$", name, re.I):
        name = name + ".asm"

    # ЖИВОЙ ФАКТ 23.09.2026: CREOSON отдаёт состав только для ОТКРЫТОЙ модели («File ... was not open»),
    # поэтому сначала открываем её без показа (как делает дом в creo_tools: file open display=False),
    # а в конце — убираем из сессии, чтобы не копить модели.
    opened = False
    if open_if_needed:
        try:
            d = os.path.dirname(str(path)) if path else ""
            CT.creo_call("file", "open", {"file": name, "dir": d, "display": False}, timeout)
            opened = True
        except Exception as e:
            return None, "не открыть модель для состава: %s" % e
    try:
        j = CT.creo_call("bom", "get_paths",
                         {"file": name, "paths": False, "top_level": False, "exclude_inactive": True},
                         timeout)
        if not isinstance(j, dict) or (j.get("status") or {}).get("error"):
            return None, "ответ сессии: %s" % ((j or {}).get("status") or j)
        root = j.get("data") or {}
        rows, seen = [], set()

        def kids(n):
            """Ключи дерева состава — как в доме (creo_tools._kids): проверены живой сессией."""
            if not isinstance(n, dict):
                return []
            c = n.get("children")
            if isinstance(c, dict):
                c = c.get("children") or []
            return c or n.get("components") or n.get("models") or n.get("paths") or n.get("submodels") or []

        def walk(node, level=1):
            if level > 9 or len(rows) > 5000:
                return
            if isinstance(node, list):
                for x in node:
                    walk(x, level)
                return
            if not isinstance(node, dict):
                return
            f = node.get("file") or ""
            if f:
                key = (f.lower(), level)
                if key not in seen:
                    seen.add(key)
                    rows.append({"level": level, "name": f, "base": base_of(f),
                                 "qty": node.get("quantity", 1), "path": None, "kind": kind_of(f),
                                 "has_pdf": False, "pdf": None, "live": True})
            for ch in kids(node):
                walk(ch, level + 1)

        walk(root, 1)
    except Exception as e:
        return None, "состав из сессии не получен: %s" % e
    finally:
        if opened and cleanup:
            try:
                CT.creo_call("file", "erase", {"file": name}, 15)
            except Exception:
                pass
    if not rows:
        return None, "сессия не вернула позиций (пустая сборка или другое имя)"
    return rows, None


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


def path_of(name):
    """Публичная обёртка: где лежит файл с таким именем (по индексу дома). Нужна окну."""
    return _path_of(None, name)


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