# -*- coding: utf-8 -*-
import re, gzip, io, datetime, urllib.request, urllib.parse
import settings, core
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0.0.0 Safari/537.36"
HDR = {"User-Agent": UA, "Accept": "text/html,*/*;q=0.8", "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.5", "Accept-Encoding": "gzip"}
def norm_url(u): return urllib.parse.quote(u, safe=":/?#[]@!$&'()*+,;=%")
def _get(u, t=15, h=None):
    with urllib.request.urlopen(urllib.request.Request(u, headers=h or HDR), timeout=t) as r:
        d = r.read()
        if r.headers.get("Content-Encoding") == "gzip": d = gzip.GzipFile(fileobj=io.BytesIO(d)).read()
        return d.decode(r.headers.get_content_charset() or "utf-8", "ignore"), r.status
def clean(h):
    h = re.sub(r"(?is)<(script|style|noscript|svg|head).*?>.*?</\1>", " ", h)
    h = re.sub(r"(?s)<!--.*?-->", " ", h); h = re.sub(r"(?is)<(p|div|br|tr|li|h\d)[^>]*>", "\n", h)
    h = re.sub(r"(?s)<[^>]+>", " ", h)
    for a,b in (("&nbsp;"," "),("&amp;","&"),("&lt;","<"),("&gt;",">"),("&quot;",'"')): h = h.replace(a,b)
    h = re.sub(r"&#\d+;", " ", h); h = re.sub(r"[ \t]+", " ", h); return re.sub(r"\n\s*\n+", "\n", h).strip()
def _t_direct(u):
    try:
        h, st = _get(norm_url(u), 15); return (h, "direct") if st < 400 and h else (None, "direct:%s" % st)
    except Exception as e: return None, "direct:%s" % str(e)[:50]
def _t_all(u):
    try:
        t, st = _get("https://api.allorigins.win/raw?url=" + urllib.parse.quote(u, safe=""), 20)
        return (t, "allorigins") if st < 400 and len(t) > 100 else (None, "allorigins:%s" % st)
    except Exception as e: return None, "allorigins:%s" % str(e)[:50]
def _t_jina(u):
    h = dict(HDR); k = (settings.get("web_jina_key") or "").strip()
    if k: h["Authorization"] = "Bearer " + k
    try:
        t, st = _get("https://r.jina.ai/" + u, 30, h); return (t, "jina") if st < 400 and len(t) > 100 else (None, "jina:%s" % st)
    except Exception as e: return None, "jina:%s" % str(e)[:50]
def _t_pw(u):
    if not settings.get("web_render"): return None, "playwright:выкл"
    try: from playwright.sync_api import sync_playwright
    except Exception: return None, "playwright:нет"
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True); pg = b.new_page(user_agent=UA)
            pg.goto(u, timeout=30000, wait_until="domcontentloaded"); pg.wait_for_timeout(2500)
            h = pg.content(); b.close()
        return (h, "playwright") if h and len(h) > 200 else (None, "playwright:пусто")
    except Exception as e: return None, "playwright:%s" % str(e)[:50]
def fetch(u):
    att = []
    for fn in (_t_direct, _t_all, _t_jina, _t_pw):
        h, tag = fn(u)
        if h is not None: return h, tag, att
        att.append(tag)
    return None, "error", att
def tool_web_fetch(url="", **kw):
    if not url: return "нужна ссылка"
    h, src, att = fetch(url)
    return "[%s] %s" % (src, clean(h)[:4000]) if h else "не открылось | %s" % " -> ".join(att)
def tool_web_study(url="", mode="quick", **kw):
    if not url: return "нужна ссылка"
    h, src, att = fetch(url)
    if not h: return "не открылось | %s" % " -> ".join(att)
    t = clean(h) if src != "jina" else h
    return ("[источник: %s | %s]\n%s\n[перескажи по-русски: суть + факты + применимость к Creo/КБ]" % (url, src, t[: (6000 if str(mode)=="deep" else 2500)]))
def tool_web_save_rule(kind="skill", name="", text="", **kw):
    if not (text or "").strip(): return "пусто"
    nm = re.sub(r"[^A-Za-zА-Яа-я0-9_.-]+", "_", (name or "web").strip())[:60] or "web"
    p = (core.REPO / "Ошибки" / ("ERR_%s_%s.md" % (datetime.datetime.now().strftime("%y%m%d"), nm))) if kind == "err" else (core.REPO / ("SKILL_web_%s.md" % nm))
    p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text, encoding="utf-8")
    return "сохранено: %s" % p.name
TOOLS = [
 {"name": "web_fetch", "desc": "Скачать страницу (цепочка фолбэков)", "params": {"url": "ссылка"}, "approval": False, "fn": tool_web_fetch},
 {"name": "web_study", "desc": "Изучить ссылку + пересказ", "params": {"url": "ссылка", "mode": "quick/deep"}, "approval": False, "fn": tool_web_study},
 {"name": "web_save_rule", "desc": "Записать итог в репо", "params": {"kind": "skill/err", "name": "имя", "text": "суть"}, "approval": True, "fn": tool_web_save_rule},
]

def fetch_html(u):
    return fetch(u)
