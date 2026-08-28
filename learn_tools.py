import re, datetime
import core
from core import log
import settings
import creo_tools as CT

PROMPT = ("Ты — старший инженер-конструктор. Дана ЭТАЛОННАЯ модель Creo.\n"
          "Модель: %s\nСвойства: %s\nПАРАМЕТРЫ:\n%s\nОТНОШЕНИЯ:\n%s\n"
          "Извлеки КОНСТРУКТОРСКИЕ ПРАВИЛА по-русски: входные и выводные "
          "параметры, порядок расчёта, ограничения, что нельзя ломать. Кратко.")

def _clean(s):
    return re.sub(r"[^A-Za-zА-Яа-я0-9_\-]", "_", str(s or "").strip())[:60] or "object"

def tool_learn(name="", **kw):
    nm = name or CT.tool_get_active()
    params = CT.tool_get_params(nm)
    rels = CT.tool_get_relations(nm)
    mass = CT.tool_get_mass(nm)
    if not rels or rels == "отношений нет" or rels.startswith("ошибка"):
        return "модель %s без отношений — учить нечему" % nm
    try:
        r = core.post("/api/chat", {"model": settings.get("llm_model") or "deepseek-r1:14b",
                                    "stream": False, "options": {"temperature": 0.2, "num_predict": 2048},
                                    "messages": [{"role": "user", "content": PROMPT % (nm, mass, params, rels)}]}, t=300)
        rules = (r.get("message") or {}).get("content") or ""
        rules = rules.split(TOK)[0].strip()
    except Exception as e:
        return "ИИ не извлёк правила: %s" % e
    des = _clean(nm)
    p = core.REPO / ("SKILL_object_%s.md" % des)
    body = ("---\nname: object_%s\nsystem: обучение\n"
            "description: Use when: вопросы об объекте %s и создание похожих\n"
            "source_model: %s\nlearned: %s\n---\n\n"
            "# ОБЪЕКТ %s (выучено из эталона)\n\n"
            "## ПАРАМЕТРЫ\n%s\n\n## ОТНОШЕНИЯ\n%s\n\n## ПРАВИЛА\n%s\n"
            % (des, nm, nm, datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), nm, params, rels, rules))
    p.write_text(body, encoding="utf-8")
    log("learn: сохранён %s" % p.name)
    return "Выучил %s → %s. Правила:\n%s" % (nm, p.name, rules[:1200])

def tool_rules(q="", **kw):
    hits = []
    for p in sorted(core.REPO.glob("SKILL_object_*.md")):
        txt = p.read_text(encoding="utf-8", errors="ignore")
        if not q or q.lower() in p.name.lower() or q.lower() in txt.lower():
            hits.append((p, txt))
    if not hits: return "выученных объектов нет"
    out = []
    for p, txt in hits[:3]:
        m = re.search(r"## ПРАВИЛА\n([\s\S]*)", txt)
        out.append("=== %s ===\n%s" % (p.name, (m.group(1) if m else txt)[:1200]))
    return "\n\n".join(out)

TOK = "<|im_end|>"

TOOLS = [
    {"name": "model_learn", "desc": "Обучиться на эталонной модели: параметры+отношения+масса → правила → скилл в базу", "params": {"name": "модель (пусто = активная)"}, "approval": True, "fn": tool_learn},
    {"name": "model_rules", "desc": "Показать выученные конструкторские правила объекта", "params": {"q": "шифр или слово"}, "approval": False, "fn": tool_rules},
]
