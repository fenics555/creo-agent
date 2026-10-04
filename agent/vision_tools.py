# -*- coding: utf-8 -*-
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


def _vision_backend() -> str:
    """04.10.2026 (аудит настроек): `vision_backend`, `vision_url`, `vision_gpu` были объявлены
    в панели, но визия всегда ходила только в Ollama и только по модели — три настройки были
    обещанием впустую. Теперь можно выбрать бэкенд Ollama или локальный llama.cpp (OpenAI-совместимый)."""
    try:
        b = str(settings.get("vision_backend") or "ollama").strip().lower()
    except Exception:
        b = "ollama"
    return b if b in ("ollama", "llamacpp") else "ollama"


def _llamacpp_analyze(f, prompt):
    """Анализ через llama.cpp: vision_url (OpenAI-совместимый /v1/chat/completions), vision_gpu — слоёв на GPU."""
    base = str(settings.get("vision_url") or "").strip().rstrip("/")
    if not base:
        return "vision_backend=llamacpp, но vision_url пуст. Укажи адрес сервера (например http://127.0.0.1:8080)."
    try:
        gpu = int(settings.get("vision_gpu") or 0)
    except Exception:
        gpu = 0
    payload = {"model": "local",
               "messages": [{"role": "user", "content": [
                   {"type": "text", "text": prompt},
                   {"type": "image_url", "image_url": {"url": "data:image/png;base64," + _b64(f)}}]}],
               "temperature": 0.2}
    if gpu > 0:
        payload["n_gpu_layers"] = gpu
    import json as _json
    import urllib.request as _ur
    req = _ur.Request(base + "/v1/chat/completions", data=_json.dumps(payload).encode("utf-8"),
                      headers={"Content-Type": "application/json"})
    with _ur.urlopen(req, timeout=180) as r:
        j = _json.loads(r.read().decode("utf-8", "ignore"))
    txt = ((j.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    return "📷 %s (llamacpp %s, gpu-слоёв: %d):\n%s" % (f.name, base, gpu, txt.strip() or "пусто")

def tool_vision_analyze(q="", **kw):
    SHOTS.mkdir(parents=True, exist_ok=True)
    files = sorted(SHOTS.glob("*.png"), key=lambda p: p.stat().st_mtime)
    if not files:
        return "скриншотов нет. Нажми Ctrl-V в поле ввода и отправь вопрос — я сохраню PNG и разберу его."
    f = files[-1]
    prompt = (q or "Опиши, что на скриншоте: окна, модели, ошибки, кнопки. Кратко и по делу.")

    # 04.10.2026 (аудит настроек): бэкенд выбирается настройкой `vision_backend`.
    # Ollama (по умолчанию) ведёт себя как раньше; llama.cpp — локальный сервер vision_url.
    if _vision_backend() == "llamacpp":
        try:
            return _llamacpp_analyze(f, prompt)
        except Exception as e:
            return "llamacpp не ответил: %s" % str(e)[:150]
    
    # ЖИВАЯ НАХОДКА 24.09.2026: здесь первым брался СКРЫТЫЙ ключ vision_model (в нём по умолчанию
    # неустановленный qwen2-vl:7b), из-за чего визия каждый раз пробовала несуществующую модель.
    # Правильный порядок: настроенная роль model_vision -> старый vision_model -> запасные.
    _vm = settings.get("model_vision") or settings.get("vision_model") or "gemma4:12b"
    raw_candidates = [_vm, "gemma4:12b", "gemma4:26b"]
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
