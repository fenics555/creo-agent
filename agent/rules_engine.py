# -*- coding: utf-8 -*-
r"""rules_engine.py — ДВИЖОК ПРАВИЛ ДОМА (волна 4, этап 2 плана).

АРХИТЕКТУРА ВЗЯТА У ВЕНДОРА (`repo\B&W\13_ДВИЖОК_ПРАВИЛ.md`, схема правила из `rule.xml`):
    правило · цель (объект) · критерий · условие, соединённые логикой and/or,
    плюс ссылка «что применить» (действие/цвет).
У вендора 61 правило и 986 критериев; логика — конъюнкции (1272 and против 23 or).
Значит и наш движок по умолчанию — «И», «ИЛИ» поддержан, но им rarely пользуются.

ДВА ВИДА ОДНОГО ПРАВИЛА (константа 6 волны 1 — «правила и текст, и форма»):
  - ФОРМА: JSON `data\rules.json` — его читает движок;
  - ТЕКСТ: `IF … THEN … END_IF` — его читает человек, `to_text()` печатает.

ПРАВИЛО (JSON):
    {"id": "holes_first", "label": "Сверлить первым", "enabled": true,
     "target": {"kind": "feature", "name": "EMX_SURFACE_FUNCTION"},
     "criteria": [{"type": "param_value", "op": "regexp_match", "value": ".*_BORE_FIRST"}],
     "action": {"type": "report", "value": "сверление до остальных операций"},
     "notes": "…"}

ОПЕРАЦИИ: equal, unequal, bool, regexp_match, contains, less, greater, less_equal, greater_equal.
"""
import json
import re
from pathlib import Path

AGENT = Path(__file__).resolve().parent
RULES_FILE = AGENT / "data" / "rules.json"
SCHEMA_VERSION = 1

OPS = ("equal", "unequal", "bool", "regexp_match", "contains",
       "less", "greater", "less_equal", "greater_equal")
CRITERIA_TYPES = ("parameter", "param_value", "item_name", "group",
                  "feature", "feat_type", "component")


class RuleError(Exception):
    """Правило или файл правил нечитаемы — с честным текстом, не молча."""


def validate(doc):
    """Проверка документа правил. Возвращает список ошибок (пусто = валиден)."""
    errs = []
    if not isinstance(doc, dict):
        return ["корень должен быть объектом, а не %s" % type(doc).__name__]
    if doc.get("schema") != SCHEMA_VERSION:
        errs.append("schema=%s, ожидался %s" % (doc.get("schema"), SCHEMA_VERSION))
    rules = doc.get("rules")
    if not isinstance(rules, list):
        return errs + ["rules должен быть списком"]
    ids = set()
    for i, r in enumerate(rules):
        if not isinstance(r, dict):
            errs.append("правило #%d не объект" % i)
            continue
        rid = str(r.get("id") or "").strip()
        if not rid:
            errs.append("правило #%d: нет id" % i)
        elif rid in ids:
            errs.append("правило #%d: дубль id «%s»" % (i, rid))
        else:
            ids.add(rid)
        if not str(r.get("label") or "").strip():
            errs.append("правило %s: нет label" % (rid or i))
        cr = r.get("criteria")
        if not isinstance(cr, list) or not cr:
            errs.append("правило %s: criteria должен быть непустым списком" % (rid or i))
        else:
            for j, c in enumerate(cr):
                if not isinstance(c, dict):
                    errs.append("правило %s: критерий #%d не объект" % (rid or i, j))
                    continue
                if c.get("op") not in OPS:
                    errs.append("правило %s: неизвестная операция %r (есть %s)"
                                % (rid or i, c.get("op"), ", ".join(OPS)))
                if c.get("type") not in CRITERIA_TYPES:
                    errs.append("правило %s: неизвестный тип %r" % (rid or i, c.get("type")))
    return errs


def load(path=None):
    """Читает документ правил. Возвращает (doc, ошибка|None)."""
    p = Path(path or RULES_FILE)
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, "файла правил нет: %s" % p
    except Exception as e:
        return None, "файл правил не читается (%s): %s" % (p, e)
    errs = validate(doc)
    if errs:
        return doc, "правила неполны: %s" % "; ".join(errs[:5])
    return doc, None
def save(doc, path=None):
    """Сохраняет документ правил. Перед записью проверяет — мусор не пишем."""
    errs = validate(doc)
    if errs:
        raise RuleError("не сохранено: %s" % "; ".join(errs[:5]))
    p = Path(path or RULES_FILE)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(p)


def _cmp(op, got, want):
    """Одна операция. Числа сравниваются числами, остальное — строкой."""
    if op == "equal":
        return str(got) == str(want)
    if op == "unequal":
        return str(got) != str(want)
    if op == "bool":
        b = str(got).strip().lower()
        return (b in ("1", "true", "yes", "да")) == (str(want).strip().lower()
                                                    in ("1", "true", "yes", "да"))
    if op == "regexp_match":
        try:
            return re.search(str(want), str(got)) is not None
        except re.error as e:
            raise RuleError("кривый регулярный вызов %r: %s" % (want, e))
    if op == "contains":
        return str(want) in str(got)
    try:
        a, b = float(got), float(want)
    except (TypeError, ValueError):
        return False
    return {"less": a < b, "greater": a > b,
            "less_equal": a <= b, "greater_equal": a >= b}[op]


def get_field(obj, ctype):
    """Достаёт значение критерия из объекта (словаря фактов)."""
    if not isinstance(obj, dict):
        return None
    if ctype == "parameter":
        return obj.get("parameter")
    if ctype == "param_value":
        return obj.get("param_value")
    if ctype == "item_name":
        return obj.get("item_name")
    if ctype == "group":
        return obj.get("group")
    if ctype == "feature":
        return obj.get("feature")
    if ctype == "feat_type":
        return obj.get("feat_type")
    if ctype == "component":
        return obj.get("component")
    return obj.get(ctype)


def check_rule(rule, obj):
    """Проверяет правило против объекта. Возвращает (совпало, подробности[list])."""
    target = rule.get("target") or {}
    detail = []
    if target:
        tk = target.get("kind")
        tv = str(target.get("name") or "")
        real = str(get_field(obj, tk) or "")
        if tk and tv and tv.lower() != real.lower():
            return False, ["цель не та: %s=%s (ищем %s)" % (tk, real or "—", tv)]
    for c in rule.get("criteria") or []:
        got = get_field(obj, c.get("type"))
        try:
            good = _cmp(c.get("op"), got, c.get("value"))
        except RuleError as e:
            return False, [str(e)]
        detail.append("%s %s %r → %s (получено %r)"
                      % (c.get("type"), c.get("op"), c.get("value"),
                         "ДА" if good else "нет", got))
        if not good:              # критерии соединяются конъюнкцией (как у вендора)
            return False, detail
    return True, detail


def run(objects, doc=None, only=None):
    """Прогоняет правила по объектам. Возвращает сводку и совпадения."""
    doc = doc or load()[0]
    if not doc:
        return {"error": "правил нет", "rules": 0, "objects": 0, "hits": []}
    hits, considered = [], 0
    for r in doc.get("rules") or []:
        if not r.get("enabled", True):
            continue
        if only and r.get("id") not in only:
            continue
        considered += 1
        for o in objects:
            good, detail = check_rule(r, o)
            if good:
                hits.append({"rule": r["id"], "label": r.get("label"),
                             "object": o.get("item_name") or o.get("feature") or "—",
                             "action": (r.get("action") or {}).get("value", ""),
                             "detail": detail})
    return {"error": None, "rules": considered, "objects": len(objects), "hits": hits}


def to_text(rule):
    """ОДНО правило текстом (вид B&W: IF … THEN … END_IF)."""
    lines = ['IF %s == "%s"' % ((rule.get("target") or {}).get("kind", "object"),
                                (rule.get("target") or {}).get("name", "*"))]
    for c in rule.get("criteria") or []:
        lines.append('   %s %s "%s"' % (c.get("type"), c.get("op"), c.get("value")))
    lines.append('THEN %s' % (rule.get("action") or {}).get("value", "—"))
    lines.append("END_IF")
    return "\n".join(lines)


def all_text(doc=None):
    """Все правила текстом, в порядке файла (порядок важен — как у вендора)."""
    doc = doc or load()[0]
    return "\n\n".join(to_text(r) for r in (doc or {}).get("rules") or [])


def move(doc, rid, delta):
    """Порядок правил важен: сдвиг на delta (-1 вверх, +1 вниз). Возвращает новый индекс."""
    rules = doc.get("rules") or []
    i = next((k for k, r in enumerate(rules) if r.get("id") == rid), None)
    if i is None:
        raise RuleError("нет правила %r" % rid)
    j = i + delta
    if not (0 <= j < len(rules)):
        return i
    rules[i], rules[j] = rules[j], rules[i]
    return j


def stats(doc=None):
    """Сводка: сколько правил, по типам критериев и операциям (как у вендора: 61/986)."""
    doc = doc or load()[0]
    rules = (doc or {}).get("rules") or []
    by_type, by_op, crit = {}, {}, 0
    for r in rules:
        for c in r.get("criteria") or []:
            crit += 1
            by_type[c.get("type")] = by_type.get(c.get("type"), 0) + 1
            by_op[c.get("op")] = by_op.get(c.get("op"), 0) + 1
    return {"rules": len(rules), "criteria": crit,
            "enabled": sum(1 for r in rules if r.get("enabled", True)),
            "by_type": by_type, "by_op": by_op}


if __name__ == "__main__":
    doc, err = load()
    print("rules.json: %s" % (err or "прочитан, ошибок нет"))
    s = stats(doc)
    print("правил: %d (включено %d), критериев: %d" % (s["rules"], s["enabled"], s["criteria"]))
    print("по типам: %s" % s["by_type"])
    print("по операциям: %s" % s["by_op"])
    print("-" * 78)
    print(all_text(doc))