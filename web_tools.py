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

import re as WR
import core as WC
import urllib.request as WU
import urllib.parse as WUP
import datetime as WDT

def _ws_fetch(url, t=10):
    r = WU.Request(url, headers={"User-Agent": "Mozilla/5.0 (agent)"})
    with WU.urlopen(r, timeout=t) as resp:
        return resp.read().decode(resp.headers.get_content_charset() or "utf-8", "ignore")

def _ws_flags(html, text):
    fl = []
    if WR.search(r"captcha|бот|не робот|BotHunt|подтвердите", html, WR.I): fl.append("captcha/антибот")
    if len(text) < 200 and WR.search(r'id=["\']?(root|app|__next)', html, WR.I): fl.append("SPA (JS)")
    if WR.search(r'<input[^>]*type=["\']password', html, WR.I) and len(text) < 600: fl.append("стена логина")
    return fl

def _ws_links(html, base, host):
    out = []
    for m in WR.finditer(r'href=["\']([^"\'#]+)["\']', html):
        u = m.group(1)
        if u.startswith(("mailto:", "javascript:")): continue
        u = WUP.urljoin(base, u)
        if u.startswith("http") and WUP.urlparse(u).netloc == host: out.append(u)
    return list(dict.fromkeys(out))

def tool_web_study(url="", mode="quick", **kw):
    import settings
    if not url: return "нужна ссылка"
    deep = str(mode) == "deep"
    try: html0 = _ws_fetch(url)
    except Exception as e: return "не открылось: %s" % str(e)[:80]
    host = WUP.urlparse(url).netloc
    pages, seen = [(url, html0)], {url}
    maxp = int(settings.get("web_deep_pages") or 50) if deep else 1 + int(settings.get("web_quick_links") or 10)
    per = 2000 if deep else 1200
    for u in _ws_links(html0, url, host):
        if len(pages) >= maxp: break
        if u in seen: continue
        seen.add(u)
        try: pages.append((u, _ws_fetch(u)))
        except Exception: continue
    out = ["WEB STUDY (%s): %s — страниц: %d" % ("глубоко" if deep else "бегло", host, len(pages))]
    allfl = []
    for u, h in pages:
        t = WC.clean(h)
        allfl += _ws_flags(h, t)
        m = WR.search(r"<title[^>]*>(.*?)</title>", h, WR.S | WR.I)
        title = WR.sub(r"\s+", " ", m.group(1)).strip()[:80] if m else ""
        out.append("— %s | %s\n%s" % (title or u, u, t[:per]))
    if allfl: out.append("ПРЕДУПРЕЖДЕНИЯ: %s" % "; ".join(sorted(set(allfl))))
    out.append("")
    if deep:
        out.append("[ИНСТРУКЦИЯ АГЕНТУ: 1) пересказ ~полстраницы; 2) вердикт «поможет ли нам» по контексту чата; 3) предложи «создать правило? да/нет»; при «да» — web_save_rule с сутью.]")
    else:
        out.append("[ИНСТРУКЦИЯ АГЕНТУ: 1) пересказ ~полстраницы; 2) вердикт «поможет ли нам» по контексту чата; 3) если полезно — предложи глубокий режим (web_study mode=deep).]")
    return "\n".join(out)

def tool_web_save_rule(kind="skill", name="", text="", **kw):
    if not (text or "").strip(): return "пустой текст правила"
    nm = WR.sub(r"[^A-Za-zА-Яа-я0-9_.-]+", "_", (name or "web").strip())[:60] or "web"
    if kind == "err":
        d = WC.REPO / "Ошибки"; d.mkdir(parents=True, exist_ok=True)
        p = d / ("ERR_%s_%s.md" % (WDT.datetime.now().strftime("%y%m%d"), nm))
    else:
        p = WC.REPO / ("SKILL_web_%s.md" % nm)
    p.write_text(text, encoding="utf-8")
    return "сохранено: %s (в индекс — после рескана)" % p.name

TOOLS += [
    {"name": "web_study", "desc": "Изучить ссылку: беглый проход (главная + ссылочные), пересказ + вердикт «поможет»; mode=deep — глубоко и предложить правило", "params": {"url": "ссылка", "mode": "quick/deep"}, "approval": False, "fn": tool_web_study},
    {"name": "web_save_rule", "desc": "Записать итог изучения в репо: SKILL_web_*.md или Ошибки/ERR_*.md", "params": {"kind": "skill/err", "name": "имя", "text": "суть"}, "approval": False, "fn": tool_web_save_rule},
]
