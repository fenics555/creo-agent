# -*- coding: utf-8 -*-
r"""
АГЕНТ v12 — БЛОК ВИЗИИ (vision_tools.py)
Глаза: анализ скриншотов через Ollama vision или llamacpp.
При недоступности визии — маркер, ЗАПРЕЩАЮЩИЙ выдумывать содержимое скриншота.
"""
import base64, json, time, datetime, urllib.request
import core
from core import log, post, trace
import settings

IMG = core.BASE / "images"

def save_image(b64, client):
    d = IMG / client; d.mkdir(parents=True, exist_ok=True)
    p = d / (datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S") + ".png")
    p.write_bytes(base64.b64decode(b64)); return p

def vision_read(b64, q):
    if (settings.get("vision_backend") or "ollama") == "llamacpp":
        t0 = time.time()
        body = {"messages": [{"role": "user", "content": [{"type": "text", "text": q},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,%s" % b64}}]}], "max_tokens": 1024}
        r = urllib.request.Request((settings.get("vision_url") or "http://127.0.0.1:8081") + "/v1/chat/completions",
                                   json.dumps(body).encode(), {"Content-Type": "application/json"})
        j = json.load(urllib.request.urlopen(r, timeout=60))
        trace("VISION llamacpp", "OK", int((time.time() - t0) * 1000))
        return j["choices"][0]["message"]["content"]
    t0 = time.time()
    r = post("/api/chat", {"model": settings.get("vision_model") or "qwen2-vl:7b", "stream": False,
                           "options": {"num_gpu": settings.get("vision_gpu") or 0},
                           "messages": [{"role": "user", "content": q, "images": [b64]}]}, 60)
    trace("VISION ollama", "OK", int((time.time() - t0) * 1000))
    return r["message"]["content"]

def attach(q, image, client):
    if not image: return q
    try:
        save_image(image, client)
        return (q or "") + "\n\n[СОДЕРЖИМОЕ СКРИНШОТА]:\n" + vision_read(image, q or "Опиши скриншот подробно.")
    except Exception as e:
        log("визия err: %s" % e)
        return q + "\n[ВИЗИЯ НЕДОСТУПНА — НЕ выдумывай содержимое скриншота; скажи пользователю, что визия не настроена]"

def _purge_old():
    days = int(settings.get("image_days") or 7)
    if days <= 0: return
    now = time.time()
    for p in IMG.rglob("*.png"):
        try:
            if now - p.stat().st_mtime > days * 86400:
                p.unlink()
        except Exception: pass

def tool_vision(question="", client="", **kw):
    if not IMG.exists(): return "папки images нет"
    _purge_old()
    base = IMG / (client or "server")
    if not base.exists(): return "у вас нет скриншотов (папка пуста)"
    pngs = sorted(base.glob("*.png"), key=lambda f: f.stat().st_mtime)
    if not pngs: return "у вас нет скриншотов"
    b64 = base64.b64encode(pngs[-1].read_bytes()).decode()
    try: return vision_read(b64, question or "опиши подробно, что на экране")
    except Exception as e: return "визия недоступна: %s" % e


TOOLS = [
    {"name": "vision_analyze", "desc": "Разобрать последний скриншот из images", "params": {"question": "что искать"}, "approval": False, "fn": tool_vision},
]