import os
content = r'''# -*- coding: utf-8 -*-
"""VISION: скриншоты (Ctrl-V) + анализ через Ollama-визион."""
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
        return q + "\n[СЛУЖЕБНОЕ: прикреплён скриншот %s — если вопрос про экран, разбери его через vision_analyze.]" % fn
    except Exception:
        return q

def _b64(p): return base64.b64encode(Path(p).read_bytes()).decode()

def tool_vision_analyze(q="", **kw):
    SHOTS.mkdir(parents=True, exist_ok=True)
    files = sorted(SHOTS.glob("*.png"), key=lambda p: p.stat().st_mtime)
    if not files:
        return "скриншотов нет. Нажми Ctrl-V в поле ввода и отправь вопрос — я сохраню PNG и разберу его."
    f = files[-1]
    prompt = (q or "Опиши, что на скриншоте: окна, модели, ошибки, кнопки. Кратко и по делу.")
    
    # New candidate logic
    raw_candidates = [settings.get("vision_model") or "minicpm-v:8b", "minicpm-v:8b", "gemma4:26b"]
    candidates = []
    for c in raw_candidates:
        if c not in candidates:
            candidates.append(c)
            
    tried = []
    for m in candidates:
        tried.append(m)
        try:
            r = core.post("/api/generate", {"model": m, "prompt": prompt, "images": [_b64(f)], "stream": False}, t=120)
            return "📷 %s (%s):\n%s" % (f.name, m, (r.get("response") or "").strip() or "пусто")
        except Exception:
            continue
            
    return "визион-модели не ответили. Проверены: %s. Проверь ollama list." % ", ".join(tried)

TOOLS = [
    {"name": "vision_analyze", "desc": "Разобрать последний прикреплённый скриншот (Ctrl-V) через визион-модель", "params": {"q": "вопрос по скриншоту"}, "approval": False, "fn": tool_vision_analyze},
]
'''
with open(r'D:\AI\tools\agent\vision_tools.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Success")
