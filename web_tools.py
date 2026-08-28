# -*- coding: utf-8 -*-
r"""АГЕНТ v12 — БЛОК WEB (web_tools.py). Чтение страниц с правильной кодировкой."""
import re, io, gzip, urllib.request
import core
from core import log

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def _decode(raw, headers):
    try: enc = headers.get_content_charset()
    except Exception: enc = None
    for e in ([enc] if enc else []) + ["utf-8", "cp1251"]:
        try: return raw.decode(e)
        except Exception: pass
    return raw.decode("utf-8", errors="ignore")

def tool_fetch(url="", save=0, **kw):
    if not url: return "нужна ссылка"
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20)
        raw = r.read()
        if (r.headers.get("Content-Encoding") or "") == "gzip":
            raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
        txt = _decode(raw, r.headers)
    except Exception as e:
        return "не смог открыть ссылку: %s (сохрани страницу локально и дай файл)" % e
    txt = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", txt, flags=re.I)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    if save:
        try:
            p = core.REPO / "Web"; p.mkdir(parents=True, exist_ok=True)
            name = url.split("?")[0].rstrip("/").split("/")[-1] or "page"
            (p / (name[:60] + ".txt")).write_text(txt[:200000], encoding="utf-8")
        except Exception as e:
            log("web save err: %s" % e)
    return txt[:6000] or "страница пустая"

TOOLS = [
    {"name": "web_fetch", "desc": "Открыть ссылку и вернуть текст страницы (чтение), save=1 — копия в репо/Web", "params": {"url": "ссылка", "save": "0/1"}, "approval": False, "fn": tool_fetch},
]