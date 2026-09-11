# -*- coding: utf-8 -*-
"""PDF-глаза: страницы, миниатюры, свежесть, перепечать через CREOSON."""
import json
import datetime
import urllib.request
from pathlib import Path
try:
    import pymupdf as fitz
except Exception:
    import fitz
import core
import settings

PDFCACHE = Path(r"D:\AI\tools\agent\data\pdfcache")
PDFCACHE.mkdir(parents=True, exist_ok=True)
CREOSON_URL = "http://127.0.0.1:8080/creoson"


def _get_file_info(name):
    """(pdf, drw, prt) как (path, mtime) или None.
    pdf ищем точным совпадением.stem; drw/prt — точно ИЛИ с m-префиксом
    (чертежи сборок зовутся m-<имя>-...), регистр расширения любой."""
    c = core.db()
    res_pdf = c.execute(
        "SELECT path, mtime FROM files WHERE (path LIKE ? OR path LIKE ?) "
        "AND path NOT LIKE '%.tmp%' ORDER BY mtime DESC",
        (f"%{name}.pdf", f"%{name}.PDF")).fetchone()
    res_drw = c.execute(
        "SELECT path, mtime FROM files WHERE (path LIKE ? OR path LIKE ? OR path LIKE ? OR path LIKE ?) "
        "AND path NOT LIKE '%.tmp%' ORDER BY mtime DESC",
        (f"%{name}.drw", f"%{name}.DRW", f"%\\m-{name}%.drw", f"%\\m-{name}%.DRW")).fetchone()
    res_prt = c.execute(
        "SELECT path, mtime FROM files WHERE (path LIKE ? OR path LIKE ? OR path LIKE ? OR path LIKE ?) "
        "AND path NOT LIKE '%.tmp%' ORDER BY mtime DESC",
        (f"%{name}.prt", f"%{name}.PRT", f"%\\m-{name}%.prt", f"%\\m-{name}%.PRT")).fetchone()
    c.close()
    return res_pdf, res_drw, res_prt


def pdf_pages(name):
    res_pdf, res_drw, _ = _get_file_info(name)
    if not res_pdf:
        return {"error": "нет pdf"}
    pdf_path, pdf_mtime = res_pdf
    drw_mtime = res_drw[1] if res_drw else 0
    try:
        doc = fitz.open(pdf_path)
        pages = len(doc)
        doc.close()
        return {"name": name, "pages": pages, "pdf_mtime": pdf_mtime,
                "drw_mtime": drw_mtime, "status": "ok"}
    except Exception as e:
        return {"error": f"ошибка fitz: {e}"}


def pdf_img(name, page):
    res_pdf, _, _ = _get_file_info(name)
    if not res_pdf:
        return {"error": "нет pdf"}
    pdf_path, pdf_mtime = res_pdf
    page_idx = int(page) - 1
    cache_path = PDFCACHE / f"{Path(pdf_path).name}_{pdf_mtime}_{page}.png"
    if cache_path.exists():
        return {"image_path": str(cache_path)}
    try:
        doc = fitz.open(pdf_path)
        if page_idx >= len(doc):
            return {"error": "страница вне диапазона"}
        pix = doc[page_idx].get_pixmap(dpi=80)
        pix.save(str(cache_path))
        doc.close()
        return {"image_path": str(cache_path)}
    except Exception as e:
        return {"error": f"ошибка fitz: {e}"}


def pdf_status(name):
    res_pdf, res_drw, _ = _get_file_info(name)
    if not res_pdf:
        return {"status": "нет pdf"}
    if not res_drw:
        return {"status": "нет чертежа"}
    pdf_mtime = res_pdf[1]
    drw_mtime = res_drw[1]
    return {"status": "актуален"} if pdf_mtime >= drw_mtime else {"status": "УСТАРЕЛ"}


def pdf_refresh(name, approval=True):
    """Пишущая: перепечать PDF из чертежа через CREOSON export_pdf."""
    _, res_drw, _ = _get_file_info(name)
    if not res_drw:
        return {"error": "нет чертежа"}
    drw_path = res_drw[0]
    outdir = str(Path(drw_path).parent)
    pdf_name = Path(drw_path).stem + ".pdf"
    try:
        conn_req = urllib.request.Request(
            CREOSON_URL, json.dumps({"command": "connection", "function": "connect", "data": {}}).encode(),
            {"Content-Type": "application/json"})
        with urllib.request.urlopen(conn_req, timeout=5) as f:
            session_id = json.loads(f.read().decode())["sessionId"]
        body = {"sessionId": session_id, "command": "interface", "function": "export_pdf",
                "data": {"file": str(Path(drw_path).name), "filename": pdf_name, "dirname": outdir}}
        exec_req = urllib.request.Request(
            CREOSON_URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
        with urllib.request.urlopen(exec_req, timeout=30) as f:
            exec_res = json.loads(f.read().decode())
            if exec_res["status"]["error"]:
                return {"error": f"CREOSON error: {exec_res['status']['message']}"}
            return {"status": "ok", "details": exec_res.get("data")}
    except Exception as e:
        return {"error": f"pdf_refresh failed: {e}"}


TOOLS = [
    {"name": "pdf_pages", "desc": "Сколько страниц в PDF и его свежесть к чертежу",
     "params": {"name": "имя модели"}, "fn": pdf_pages},
    {"name": "pdf_img", "desc": "Миниатюра страницы PDF (кэш в pdfcache)",
     "params": {"name": "имя модели", "page": "номер страницы"}, "fn": pdf_img},
    {"name": "pdf_status", "desc": "Вердикт свежести: актуален / УСТАРЕЛ / нет чертежа / нет pdf",
     "params": {"name": "имя модели"}, "fn": pdf_status},
    {"name": "pdf_refresh", "desc": "Перепечать PDF из чертежа через CREOSON (пишущая)",
     "params": {"name": "имя модели"}, "approval": True, "fn": pdf_refresh},
]