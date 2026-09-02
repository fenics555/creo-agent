# -*- coding: utf-8 -*-
r"""WEB: fetch+изучение. Цепочка: direct(quote) -> allorigins -> jina(ключ) -> playwright(опц.).
Каждый шаг репортит статус; «антибот» — только при 401/403/498 от цели."""
import re, gzip, io, datetime
import urllib.request, urllib.parse
import settings
import core
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
HDR = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
       "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.5", "Accept-Encoding": "gzip"}

def norm_url(url):
    return urllib.parse.quote(url, safe=":/?#[]@!$&'()*+,;=%")

def _get(url, t=15, headers=None):
    req = urllib.request.Request(url, headers=headers or HDR)
    with urllib.request.urlopen(req, timeout=t) as r:
        data = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            data = gzip.GzipFile(fileobj=io.BytesIO(data)).read()
        enc = r.headers.get_content_charset() or "utf-8"
        return data.decode(enc, "ignore"), r.status

def clean(html):
    html = re.sub(r"(?is)<(script|style|noscript|svg|head).*?>.*?</\1>", " ", html)
    html = re.sub(r"(?s)<!--.*?-->", " ", html)
    html = re.sub(r"(?is)<(p|div|br|tr|li|h\d)[^>]*>", "\n", html)
    html = re.sub(r"(?s)<[^>]+>", " ", html)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"')):
        html = html.replace(a, b)
    html = re.sub(r"&#\d+;", " ", html)
    html = re.sub(r"[ \t]+", " ", html); html = re.sub(r"\n\s*\n+", "\n", html)
    return html.strip()

def links(html, base, host):
    out = []
    for m in re.finditer(r'(?i)<a[^>]+href=["\']([^"\'#]+)["\']', html):
        u = m.group(1)
        if u.startswith(("mailto:", "javascript:")): continue
        u = urllib.parse.urljoin(base, u)
        if u.startswith("http") and urllib.parse.urlparse(u).netloc == host: out.append(u)
    return list(dict.fromkeys(out))

def _t_direct(url):
    try:
        html, st = _get(norm_url(url), 15)
        if st < 400 and html: return html, "direct"
        return None, "direct:%s" % st
    except Exception as e: return None, "direct:%s" % str(e)[:60]

def _t_allorigins(url):
    try:
        txt, st = _get("https://api.allorigins.win/raw?url=" + urllib.parse.quote(url, safe=""), 20)
        if st < 400 and len(txt) > 100: return txt, "allorigins"
        return None, "allorigins:%s" % st
    except Exception as e: return None, "allorigins:%s" % str(e)[:60]

def _t_jina(url):
    h = dict(HDR); key = (settings.get("web_jina_key") or "").strip()
    if key: h["Authorization"] = "Bearer " + key
    try:
        txt, st = _get("https://r.jina.ai/" + url, 30, h)
        if st < 400 and len(txt) > 100: return txt, "jina"
        return None, "jina:%s(нужен ключ web_jina_key)" % st
    except Exception as e: return None, "jina:%s" % str(e)[:60]

def _t_playwright(url):
    if not settings.get("web_render"): return None, "playwright:выкл(web_render=0)"
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None, "playwright:не установлен(pip install playwright && playwright install chromium)"
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            pg = b.new_page(user_agent=UA)
            pg.goto(url, timeout=30000, wait_until="domcontentloaded")
            pg.wait_for_timeout(2500)
            html = pg.content(); b.close()
        if html and len(html) > 200: return html, "playwright"
        return None, "playwright:пусто"
    except Exception as e: return None, "playwright:%s" % str(e)[:60]

def fetch_html(url):
    att = []
    for fn in (_t_direct, _t_allorigins, _t_jina, _t_playwright):
        html, tag = fn(url)
        if html is not None: return html, tag, att
        att.append(tag)
    return None, "error", att

def tool_web_fetch(url="", **kw):
    if not url: return "нужна ссылка"
    html, src, att = fetch_html(url)
    if html is None:
        return "не открылось %s | цепочка: %s" % (url, " -> ".join(att))
    txt = clean(html) if src != "jina" else html
    return "[%s] %s" % (src, txt[:4000]) or "страница пустая (SPA/JS)"

def tool_web_study(url="", mode="quick", **kw):
    if not url: return "нужна ссылка"
    deep = str(mode) == "deep"
    html, src, att = fetch_html(url)
    if html is None:
        return "не открылось %s | цепочка: %s. Если цель под антиботом — включи web_render=1 (Playwright) или вставь текст вручную." % (url, " -> ".join(att))
    host = urllib.parse.urlparse(url).netloc
    is_html = src in ("direct", "allorigins", "playwright")
    text = clean(html) if is_html else html
    pages = [(url, text)]
    if is_html:
        lim = int(settings.get("web_deep_pages") or 50) if deep else int(settings.get("web_quick_links") or 10)
        for u in links(html, url, host)[:lim]:
            h2, s2, _ = fetch_html(u)
            if h2: pages.append((u, clean(h2) if s2 != "jina" else h2))
    out = ["WEB STUDY (%s, источник %s): страниц %d" % ("глубоко" if deep else "бегло", src, len(pages))]
    for u, t2 in pages:
        out.append("— %s\n%s" % (u, t2[: (2000 if deep else 1200)]))
    out.append("[ИНСТРУКЦИЯ: пересказ ~полстраницы + вердикт «поможет ли нам»; если полезно — предложи глубокий режим или создать правило (web_save_rule).]")
    return "\n".join(out)

def tool_web_save_rule(kind="skill", name="", text="", **kw):
    if not (text or "").strip(): return "пустой текст правила"
    nm = re.sub(r"[^A-Za-zА-Яа-я0-9_.-]+", "_", (name or "web").strip())[:60] or "web"
    if kind == "err":
        d = core.REPO / "Ошибки"; d.mkdir(parents=True, exist_ok=True)
        p = d / ("ERR_%s_%s.md" % (datetime.datetime.now().strftime("%y%m%d"), nm))
    else:
        p = core.REPO / ("SKILL_web_%s.md" % nm)
    p.write_text(text, encoding="utf-8")
    return "сохранено: %s" % p.name

TOOLS = [
 {"name": "web_fetch", "desc": "Скачать страницу текстом; цепочка direct->allorigins->jina->playwright с тегами", "params": {"url": "ссылка"}, "approval": False, "fn": tool_web_fetch},
 {"name": "web_study", "desc": "Изучить ссылку: бегло/глубоко + вердикт «поможет ли»", "params": {"url": "ссылка", "mode": "quick/deep"}, "approval": False, "fn": tool_web_study},
 {"name": "web_save_rule", "desc": "Записать итог изучения в репо (SKILL/ERR)", "params": {"kind": "skill/err", "name": "имя", "text": "суть"}, "approval": False, "fn": tool_web_save_rule},
]
