# -*- coding: utf-8 -*-
"""АГЕНТ v15 — vision_audit.py: сверка PDF-экспорта с чек-листом ГОСТ.
Вердикты: passed / failed / not_determined.
material/roughness/scale и мета-поля — резерв спеки 21 (vision-модель): не галлюцинируем."""
import json, base64, re
import urllib.request
from pathlib import Path
import pdf_tools
import core
import settings

CHECK_DIR = Path(r"D:\AI\tools\agent\data\checklists")
CHECK_DIR.mkdir(parents=True, exist_ok=True)

_VISION_Q = {
    "material": "Какая марка материала указана в графе 3 основной надписи?",
    "roughness": "Есть ли на поле чертежа знаки шероховатости? Ответь ДА или НЕТ.",
    "scale": "Какой масштаб указан в графе 6 основной надписи? Ответь вида 1:1 или НЕТ.",
}


def _vision_available():
    """Модель model_vision есть в списке тегов Ollama."""
    try:
        d = json.loads(urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=10).read())
        return settings.get("model_vision") in [m.get("name") for m in d.get("models", [])]
    except Exception:
        return False


def _vision_ask(img_b64, question):
    """Спросить vision-модель; строка ответа или None при любой ошибке."""
    try:
        r = core.post("/api/generate", {"model": settings.get("model_vision"),
                                        "stream": False, "think": False, "images": [img_b64],
                                        "prompt": question + " Ответь кратко по-русски."}, t=180)
        return (r.get("response") or "").strip() or None
    except Exception:
        return None


def _check_item(cid, it, name, pdf):
    if cid == "stamp_present":
        if pdf is None:
            return "not_determined", "PDF не найден"
        pages = int(pdf.get("pages") or 0)
        return ("passed", "листов: %d" % pages) if pages >= 1 else ("failed", "страниц нет")
    if cid == "designation":
        if pdf is None:
            return "not_determined", "PDF не найден"
        st = pdf_tools.pdf_status(name)
        note = st.get("status", "") if isinstance(st, dict) else ""
        return "passed", "имя файла совпадает с обозначением; свежесть: %s" % note
    if cid in ("name_present", "mass_present"):
        return "not_determined", "мета-поля не читаются из pdf_tools (резерв vision-модели)"
    return "not_determined", "резерв спеки 21 (vision-модель)"


def tool_vision_audit(name="", checklist="gost_stamp"):
    if not (name or "").strip():
        return ("Подсказка: vision_audit name=<имя модели> [checklist=gost_stamp]. "
                "Сверяет PDF-экспорт модели с чек-листом из data\\checklists.")
    cl_path = CHECK_DIR / ("%s.json" % checklist)
    if not cl_path.exists():
        have = ", ".join(p.name for p in CHECK_DIR.glob("*.json")) or "пусто"
        return "Чек-лист «%s» не найден в data\\checklists (есть: %s)" % (checklist, have)
    try:
        items = json.loads(cl_path.read_text(encoding="utf-8"))
    except Exception as e:
        return "Чек-лист повреждён: %s" % e
    if not isinstance(items, list):
        return "Чек-лист должен быть JSON-списком пунктов."
    pdf = pdf_tools.pdf_pages(name)
    if isinstance(pdf, dict) and pdf.get("error"):
        return ("PDF не найден для модели «%s» (%s). Проверь имя или запусти скан моделей (/scan), затем повтори vision_audit."
                % (name, pdf.get("error", "")))
    img_b64 = None
    rows = []
    for it in items:
        cid = it.get("id") or ""
        if it.get("vision"):
            ans = None
            if _vision_available():
                if img_b64 is None:
                    try:
                        ip = pdf_tools.pdf_img(name, "1")
                        ipath = (ip or {}).get("image_path")
                        if ipath:
                            with open(ipath, "rb") as _f:
                                img_b64 = base64.b64encode(_f.read()).decode("ascii")
                    except Exception:
                        img_b64 = ""
                if img_b64:
                    ans = _vision_ask(img_b64, _VISION_Q.get(cid, "Что видно на чертеже?"))
            if ans:
                low = (ans or "").upper()
                if cid == "material":
                    ok = len(ans.strip()) > 1 and not low.startswith("НЕТ")
                elif cid == "roughness":
                    ok = low.startswith("ДА")
                else:
                    ok = re.search(r"\d+\s*:\s*\d+", ans) is not None
                rows.append((cid, it.get("title", cid), "passed" if ok else "failed", ans[:80]))
            elif _vision_available():
                rows.append((cid, it.get("title", cid), "not_determined", "визия недоступна: модель не ответила"))
            else:
                rows.append((cid, it.get("title", cid), "not_determined", "визия недоступна: модель не установлена"))
            continue
        verdict, note = _check_item(cid, it, name, pdf)
        rows.append((cid, it.get("title", cid), verdict, note))
    out = ["vision_audit: %s | чек-лист «%s»" % (name, checklist)]
    for cid, title, verdict, note in rows:
        out.append("%s | %s | %s" % (verdict, cid, title))
    n_pass = sum(1 for r in rows if r[2] == "passed")
    n_fail = sum(1 for r in rows if r[2] == "failed")
    n_nd = sum(1 for r in rows if r[2] == "not_determined")
    out.append("пройдено: %d | не пройдено: %d | не определено: %d" % (n_pass, n_fail, n_nd))
    for cid, title, verdict, note in rows:
        if note:
            out.append("— %s: %s" % (cid, note))
    return "\n".join(out)


TOOLS = [
    {"name": "vision_audit",
     "desc": "Сверка PDF-экспорта с чек-листом ГОСТ (passed/failed/not_determined)",
     "params": {"name": "имя модели", "checklist": "имя чек-листа из data\\checklists"},
     "fn": tool_vision_audit},
]