# -*- coding: utf-8 -*-
r"""WEB: fetch/изучение страниц. Уважительно: браузерные заголовки, форум не трогаем."""
import re, datetime
import urllib.request, urllib.parse
import core
from core import trace
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.5"}
GUARD = ("cccp3d.ru",)
def _fetch(url, t=12):
    host = urllib.parse.urlparse(url).netloc.lower()
    if any(g in host for g in GUARD):
        return None, "форум закрыт антиботом — с сервера его не дёргаем. Открой страницу, Ctrl+A, Ctrl+C и вставь текст сюда."
    try:
        r = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(r, timeout=t) as resp:
            raw = resp.read()
        enc = resp.headers.get_content_charset() or "utf-8"
        return raw.decode(enc, "ignore"), None
    except Exception as e:
        return None, "сайт недоступен (%s). Если это форум — вставь текст вручную." % str(e)[:80]
def tool_web_fetch(url="", **kw):
    if not url: return "нужна ссылка"
    txt, err = _fetch(url)
    if err: return err
    return core.clean(txt)[:4000] or "страница пустая (возможно SPA/JS)"
def tool_web_study(url="", mode="quick", **kw):
    import settings
    if not url: return "нужна ссылка"
    deep = str(mode) == "deep"
    txt, err = _fetch(url)
    if err: return err
    host = urllib.parse.urlparse(url).netloc
    pages = [(url, txt)]
    for u in core.links(txt, url, host)[: (int(settings.get("web_deep_pages") or 50) if deep else int(settings.get("web_quick_links") or 10))]:
        t2, e2 = _fetch(u)
        if t2: pages.append((u, t2))
    out = ["WEB STUDY (%s): страниц %d" % ("глубоко" if deep else "бегло", len(pages))]
    for u, t in pages:
        out.append("— %s\n%s" % (u, core.clean(t)[: (2000 if deep else 1200)]))
    out.append("[ИНСТРУКЦИЯ: пересказ ~полстраницы + вердикт «поможет ли нам»; если да — предложи создать правило (web_save_rule).]")
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
 {"name": "web_fetch", "desc": "Скачать страницу текстом (браузерные заголовки, форум не трогаем)", "params": {"url": "ссылка"}, "approval": False, "fn": tool_web_fetch},
 {"name": "web_study", "desc": "Изучить ссылку: бегло/глубоко + вердикт «поможет ли»", "params": {"url": "ссылка", "mode": "quick/deep"}, "approval": False, "fn": tool_web_study},
 {"name": "web_save_rule", "desc": "Записать итог изучения в репо (SKILL/ERR)", "params": {"kind": "skill/err", "name": "имя", "text": "суть"}, "approval": False, "fn": tool_web_save_rule},
]
