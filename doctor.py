# -*- coding: utf-8 -*-
import json
from pathlib import Path
AG = Path(r"D:\AI\tools\agent")

# 1) уводим тестовую цель с форума + чистим config
sp = AG / "settings.py"; s = sp.read_text(encoding="utf-8")
if "cccp3d.ru" in s:
    sp.write_text(s.replace("https://cccp3d.ru", "https://www.ptc.com"), encoding="utf-8"); print("[+] settings: тест-цель -> ptc.com")
cp = AG / "data" / "config.json"
if cp.exists():
    d = json.loads(cp.read_text(encoding="utf-8"))
    if "cccp3d" in str(d.get("web_test_url", "")):
        d["web_test_url"] = "https://www.ptc.com"; cp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8"); print("[+] config: web_test_url -> ptc.com")

# 2) WEB: браузерные заголовки, guard форума, без ретраев
(AG / "web_tools.py").write_text('''# -*- coding: utf-8 -*-
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
        out.append("— %s\\n%s" % (u, core.clean(t)[: (2000 if deep else 1200)]))
    out.append("[ИНСТРУКЦИЯ: пересказ ~полстраницы + вердикт «поможет ли нам»; если да — предложи создать правило (web_save_rule).]")
    return "\\n".join(out)
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
''', encoding="utf-8"); print("[+] web_tools: заголовки + guard форума")

# 3) VISION: настоящий конвейер Ctrl+V -> PNG -> Ollama-визион
(AG / "vision_tools.py").write_text('''# -*- coding: utf-8 -*-
r"""VISION: скриншоты (Ctrl+V) + анализ через Ollama-визион."""
import base64, datetime
from pathlib import Path
import core, settings
SHOTS = Path(core.BASE) / "agent" / "data" / "shots"
def attach(q, image, client):
    if not image: return q
    try:
        SHOTS.mkdir(parents=True, exist_ok=True)
        fn = datetime.datetime.now().strftime("%y%m%d_%H%M%S") + ".png"
        (SHOTS / fn).write_bytes(base64.b64decode(image))
        return q + "\\n[СЛУЖЕБНОЕ: прикреплён скриншот %s — если вопрос про экран, разбери его через vision_analyze.]" % fn
    except Exception:
        return q
def _b64(p): return base64.b64encode(Path(p).read_bytes()).decode()
def tool_vision_analyze(q="", **kw):
    SHOTS.mkdir(parents=True, exist_ok=True)
    files = sorted(SHOTS.glob("*.png"), key=lambda p: p.stat().st_mtime)
    if not files:
        return "скриншотов нет. Нажми Ctrl+V в поле ввода и отправь вопрос — я сохраню PNG и разберу его."
    f = files[-1]
    prompt = (q or "Опиши, что на скриншоте: окна, модели, ошибки, кнопки. Кратко и по делу.")
    last = None
    for m in [settings.get("vision_model") or "qwen2-vl:7b", "moondream:1.8b"]:
        try:
            r = core.post("/api/generate", {"model": m, "prompt": prompt, "images": [_b64(f)], "stream": False}, t=120)
            return "📷 %s (%s):\\n%s" % (f.name, m, (r.get("response") or "").strip() or "пусто")
        except Exception as e:
            last = e
    return "визион-модель не ответила: %s — проверь ollama list (нужна qwen2-vl:7b или moondream:1.8b)" % last
TOOLS = [
 {"name": "vision_analyze", "desc": "Разобрать последний прикреплённый скриншот (Ctrl+V) через визион-модель", "params": {"q": "вопрос по скриншоту"}, "approval": False, "fn": tool_vision_analyze},
]
''', encoding="utf-8"); print("[+] vision_tools: Ctrl+V -> PNG -> Ollama-визион")
print("ГОТОВО: .\\AI_RESTART.bat, затем diag_web и vision_analyze")