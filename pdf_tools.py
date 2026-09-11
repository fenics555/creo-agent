import fitz
import sqlite3
import os
import datetime
import re
from pathlib import Path
import core
import settings

PDFCACHE = Path(r"D:\AI\tools\agent\data\pdfcache")
PDFCACHE.mkdir(parents=True, exist_ok=True)

def _get_file_info(name):
    """Returns (path, mtime) for a file matching name and extension."""
    c = core.db()
    res_pdf = c.execute("SELECT path, mtime FROM files WHERE path LIKE ? AND path NOT LIKE '%.tmp%'", (f"%{name}.pdf",)).fetchone()
    res_drw = c.execute("SELECT path, mtime FROM files WHERE (path LIKE ? OR path LIKE ?) AND path NOT LIKE '%.tmp%'", (f"%{name}.drw", f"%{name}.DRW")).fetchone()
    res_prt = c.execute("SELECT path, mtime FROM files WHERE (path LIKE ? OR path LIKE ?) AND path NOT LIKE '%.tmp%'", (f"%{name}.prt", f"%{name}.PRT")).fetchone()
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
        return {
            "name": name,
            "pages": pages,
            "pdf_mtime": pdf_mtime,
            "drw_mtime": drw_mtime,
            "status": "ok"
        }
    except Exception as e:
        return {"error": f"ошибка fitz: {e}"}

def pdf_img(name, page):
    res_pdf, _, _ = _get_file_info(name)
    if not res_pdf:
        return {"error": "нет pdf"}
    
    pdf_path, pdf_mtime = res_pdf
    page_idx = int(page) - 1
    
    cache_name = f"{Path(pdf_path).name}_{pdf_mtime}_{page}.png"
    cache_path = PDFCACHE / cache_name
    
    if cache_path.exists():
        return {"image_path": str(cache_path)}
    
    try:
        doc = fitz.open(pdf_path)
        if page_idx >= len(doc):
            return {"error": "страница вне диапазона"}
        
        page_obj = doc[page_idx]
        pix = page_obj.get_pixmap(dpi=80)
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
    
    pdf_path, pdf_mtime = res_pdf
    drw_path, drw_mtime = res_drw
    
    if pdf_mtime >= drw_mtime:
        return {"status": "актуален"}
    else:
        return {"status": "УСТАРЕЛ"}

def pdf_refresh(name, approval=True):
    if approval:
        return "[СОГЛАСОВАНИЕ]"
        
    res_drw, _, _ = _get_file_info(name)
    if not res_drw:
        return {"error": "нет чертежа"}
    
    drw_path, _ = res_drw
    outdir = str(Path(drw_path).parent)
    nm = Path(drw_path).stem
    pdf_name = nm + ".pdf"
    
    import urllib.request
    import json
    
    CREOSON_URL = "http://127.0.0.1:8080/creoson"
    
    try:
        conn_body = {"command":"connection","function":"connect","data":{}}
        conn_req = urllib.request.Request(CREOSON_URL, json.dumps(conn_body).encode(), {"Content-Type": "application/json"})
        with urllib.request.urlopen(conn_req, timeout=5) as f:
            conn_res = json.loads(f.read().decode())
            session_id = conn_res["sessionId"]
            
        body = {
            "sessionId": session_id,
            "command": "interface",
            "function": "export_pdf",
            "data": {
                "file": str(Path(drw_path).name),
                "filename": pdf_name,
                "dirname": outdir
            }
        }
        
        exec_req = urllib.request.Request(CREOSON_URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
        with urllib.request.urlopen(exec_req, timeout=30) as f:
            exec_res = json.loads(f.read().decode())
            if exec_res["status"]["error"]:
                return {"error": f"CREOSON error: {exec_res['status']['message']}"}
            return {"status": "ok", "details": exec_res.get("data")}
            
    except Exception as e:
        return {"error": f"pdf_refresh failed: {e}"}

TOOLS = [
    {"name": "pdf_pages", "desc": "Количество страниц в PDF", "params": {"name": "имя"}, "fn": pdf_pages},
    {"name": "pdf_img", "desc": "Получить изображение страницы PDF", "params": {"name": "имя", "page": "номер страницы"}, "fn": pdf_img},
    {"name": "pdf_status", "desc": "Проверить актуальность PDF относительно чертежа", "params": {"name": "имя"}, "fn": pdf_status},
    {"name": "pdf_refresh", "desc": "Обновить PDF из чертежа (экспорт)", "params": {"name": "имя"}, "approval": True, "fn": pdf_refresh},
]
