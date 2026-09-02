# -*- coding: utf-8 -*-
r"""WEB: fetch+изучение страниц. Прямой fetch; если антибот/таймаут — через r.jina.ai."""
import re, gzip, io, datetime
import urllib.request, urllib.parse
import settings
import core
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
def _raw(url, t=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.5", "Accept-Encoding": "gzip"})
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
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&#\d+;", " ")):
        html = re.sub(a, b, html)
    html = re.sub(r"[ \t]+", " ", html); html = re.sub(r"\n\s*\n+", "\n", html)
    return html.strip()
def fetch_html(url, t=15):
    try:
        html, st = _raw(url, t)
        if st < 400: return html, "direct"
    except Exception: pass
    try:
        txt, st = _raw("https://r.jina.ai/" + url, 30)
        return txt, "proxy"
    except Exception as e:
        return None, "error: %s" % str(e)[:80]
def links(html, base, host):
    out = []
    for m in re.finditer(r'(?i)<a[^>]+href=["\']([^"\'#]+)["\']', html):
        u = m.group(1)
        if u.startswith(("mailto:", "javascript:")): continue
        u = urllib.parse.urljoin(base, u)
        if u.startswith("http") and urllib.parse.urlparse(u).netloc == host: out.append(u)
    return list(dict.fromkeys(out))
def tool_web_fetch(url="", **kw):
    if not url: return "нужна ссылка"
    html, src = fetch_html(url)
    if html is None: return "не открылось %s (%s)" % (url, src)
    return clean(html)[:4000] if src == "direct" else html[:4000]
def tool_web_study(url="", mode="quick", **kw):
    if not url: return "нужна ссылка"
    deep = str(mode) == "deep"
    html, src = fetch_html(url)
    if html is None: return "не открылось %s (%s): сайт закрыт антиботом, прокси не помог." % (url, src)
    host = urllib.parse.urlparse(url).netloc
    text = clean(html) if src == "direct" else html
    pages = [(url, text)]
    if src == "direct":
        lim = int(settings.get("web_deep_pages") or 50) if deep else int(settings.get("web_quick_links") or 10)
        for u in links(html, url, host)[:lim]:
            h2, s2 = fetch_html(u, 10)
            if h2: pages.append((u, clean(h2) if s2 == "direct" else h2))
    out = ["WEB STUDY (%s, %s): страниц %d" % ("глубоко" if deep else "бегло", src, len(pages))]
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
 {"name": "web_fetch", "desc": "Скачать страницу текстом (прямой fetch, при антиботе — через прокси)", "params": {"url": "ссылка"}, "approval": False, "fn": tool_web_fetch},
 {"name": "web_study", "desc": "Изучить ссылку: бегло/глубоко + вердикт «поможет ли»", "params": {"url": "ссылка", "mode": "quick/deep"}, "approval": False, "fn": tool_web_study},
 {"name": "web_save_rule", "desc": "Записать итог изучения в репо (SKILL/ERR)", "params": {"kind": "skill/err", "name": "имя", "text": "суть"}, "approval": False, "fn": tool_web_save_rule},
]
