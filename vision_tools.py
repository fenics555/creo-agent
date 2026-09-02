# -*- coding: utf-8 -*-
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
        return q + "\n[СЛУЖЕБНОЕ: прикреплён скриншот %s — если вопрос про экран, разбери его через vision_analyze.]" % fn
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
            return "📷 %s (%s):\n%s" % (f.name, m, (r.get("response") or "").strip() or "пусто")
        except Exception as e:
            last = e
    return "визион-модель не ответила: %s — проверь ollama list (нужна qwen2-vl:7b или moondream:1.8b)" % last
TOOLS = [
 {"name": "vision_analyze", "desc": "Разобрать последний прикреплённый скриншот (Ctrl+V) через визион-модель", "params": {"q": "вопрос по скриншоту"}, "approval": False, "fn": tool_vision_analyze},
]
