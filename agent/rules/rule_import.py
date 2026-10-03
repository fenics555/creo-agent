# -*- coding: utf-8 -*-
r"""rule_import.py - ИМПОРТ ПРАВИЛ ИЗ ЧУЖОГО rule.xml (хвост волны 4).

Зачем: у вендора правила лежат в `rule.xml` (схема `rule_definition`), их hundreds
переписать руками нельзя. Импорт переводит ИХ схему в нашу (`data\rules.json`).

СХЕМА ВЕНДОРА (живой факт 03.10.2026, файл
`D:\AI\log\urn\bw\x\mbdtools\app\configuration\color_code\rule.xml`, 233 КБ):
    <rule name= label= description= color_definition_name=>
      <logical_and><objectives><objective type="surface"><logical_and>
        <criterion type="parameter"  condition="equal" value="EMX_SURFACE_FUNCTION">
          <logical_and>
            <criterion type="param_value" condition="equal" value="CYLINDER_COUNTERBORE"/>

ПЕРЕВОД: `type` → наш тип критерия, `condition` → операция, `value` → значение.
Критерии склеиваются по И (logical_and), как у нас в конъюнкции.
Ничего не выдумывается: чего в XML нет - не пишется; неизвестный тип виден в отчёте.

Запуск: python rule_import.py <rule.xml> [--apply]
Без `--apply` rules.json НЕ трогается: пишется только отчёт.
"""
import io
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_AGENT = _HERE.parent
for _p in (_AGENT, _HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import rules_engine as RE   # noqa: E402

REPORT_DIR = Path(r"D:\AI\log\reports")

# Перевод операций вендора -> наши. Неизвестное НЕ выдумывается: заменяется на equals
# и попадает в отчёт, чтобы человек увидел.
OPS_MAP = {"equal": "equals", "eq": "equals",
           "not_equal": "not_equals", "neq": "not_equals",
           "unequal": "not_equals",
           "bool": "equals",           # булево условие: значение true/false
           "contains": "contains",
           "starts_with": "starts_with", "begins_with": "starts_with",
           "ends_with": "ends_with",
           "greater": "gt", "less": "lt",
           "greater_equal": "ge", "greater_or_equal": "ge",
           "less_equal": "le", "less_or_equal": "le",
           "regexp_match": "regexp_match", "regex": "regexp_match"}

# Типы вендора -> наши поля объекта. Неизвестный тип виден в отчёте и уходит в param_value.
TYPES_MAP = {"parameter": "param_value", "param_value": "param_value",
             "item_name": "item_name", "group": "group",
             "feature": "feat_type", "component": "component"}


def parse_rule_xml(path):
    """Чужой rule.xml -> список правил нашей схемы + статистика неизвестных операций/типов."""
    tree = ET.parse(str(path))
    root = tree.getroot()
    rules, unknown_ops, unknown_types = [], Counter(), Counter()
    for r in root.findall("rule"):
        rid = (r.get("name") or r.get("label") or "без_имени")
        label = r.get("label") or rid
        crits = []
        for c in r.iter("criterion"):
            ct = c.get("type") or "param_value"
            cond = c.get("condition") or "equals"
            val = c.get("value") or ""
            op = OPS_MAP.get(cond)
            if op is None:
                unknown_ops[cond] += 1
                op = "equals"
            ftype = TYPES_MAP.get(ct, ct)
            if ftype not in RE.CRITERIA_TYPES:
                unknown_types[ct] += 1
                ftype = "param_value"
            crits.append({"type": ftype, "op": op, "value": val})
        if not crits:
            continue                    # правило без критериев переносить нечего
        rules.append({"id": "vnd_%s" % rid[:40].replace("-", "_"),
                      "label": label,
                      "enabled": False,     # импортированные ВЫКЛЮЧЕНЫ: сначала посмотри
                      "target": {"kind": "parameter", "name": ""},
                      "criteria": crits,
                      "action": {"type": "report",
                                 "value": r.get("description") or label},
                      "notes": "импорт из %s (%s)" % (Path(path).name,
                                                      r.get("color_definition_name") or "-")})
    return rules, dict(unknown_ops), dict(unknown_types)
def merge(doc, incoming):
    """Добавить импортированные правила, не трогая существующие (сверка по id)."""
    have = {r.get("id") for r in doc.get("rules", [])}
    added, skipped = 0, 0
    for r in incoming:
        if r["id"] in have:
            skipped += 1
            continue
        doc.setdefault("rules", []).append(r)
        added += 1
    return added, skipped


def write_report(rules, unknown_ops, unknown_types, src, added=None, skipped=None):
    import time
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rp = REPORT_DIR / ("REPORT_rule_import_%s.md" % time.strftime("%Y-%m-%d_%H%M%S"))
    out = ["# ОТЧЁТ ИМПОРТА ПРАВИЛ ИЗ rule.xml", "",
           "Источник: `%s`" % src, "",
           "Правил переведено: **%d**" % len(rules), ""]
    if unknown_ops:
        out += ["## Неизвестные операции вендора", "",
                "| Операция | Сколько | Чем заменено |", "|---|---|---|"]
        for k, v in sorted(unknown_ops.items(), key=lambda x: -x[1]):
            out.append("| %s | %d | equals |" % (k, v))
        out.append("")
    if unknown_types:
        out += ["## Неизвестные типы критериев", "",
                "| Тип | Сколько | Чем заменено |", "|---|---|---|"]
        for k, v in sorted(unknown_types.items(), key=lambda x: -x[1]):
            out.append("| %s | %d | param_value |" % (k, v))
        out.append("")
    if added is not None:
        out += ["## Итог слияния", "",
                "Добавлено: **%d** · пропущено (уже есть): **%d**" % (added, skipped), ""]
    out += ["## Правила (первые 50)", "",
            "| id | Подпись | Критериев |", "|---|---|---|"]
    for r in rules[:50]:
        out.append("| %s | %s | %d |" % (r["id"], r["label"][:50], len(r["criteria"])))
    out += ["", "## ЧТО ВАЖНО",
            "Импортированные правила сохраняются **выключенными**: сначала человек смотрит",
            "и включает нужные. Применение к живой модели проверяется кнопкой",
            "«Прогнать на модели» в окне правил."]
    rp.write_text("\n".join(out), encoding="utf-8")
    return str(rp)


def main(argv):
    src = next((a for a in argv[1:] if not a.startswith("-")), "")
    apply_flag = "--apply" in argv
    if not src or not Path(src).exists():
        print("нужен файл rule.xml: python rule_import.py <rule.xml> [--apply]")
        return 2
    rules, uo, ut = parse_rule_xml(src)
    print("ИМПОРТ ПРАВИЛ: %s" % src)
    print("  переведено правил: %d" % len(rules))
    if uo:
        print("  неизвестные операции: %s" % uo)
    if ut:
        print("  неизвестные типы: %s" % ut)
    if not apply_flag:
        rp = write_report(rules, uo, ut, src)
        print("отчёт: %s" % rp)
        print("rules.json НЕ тронут (нужен --apply, и это отдельное согласие).")
        return 0
    doc, err = RE.load()
    if doc is None:
        print("правила дома не читаются: %s" % err)
        return 2
    added, skipped = merge(doc, rules)
    doc["updated"] = "импорт %s" % Path(src).name
    try:
        p = RE.save(doc)
    except RE.RuleError as e:
        print("НЕ сохранено (схема): %s" % e)
        return 1
    rp = write_report(rules, uo, ut, src, added, skipped)
    print("добавлено: %d, пропущено: %d" % (added, skipped))
    print("сохранено: %s" % p)
    print("отчёт: %s" % rp)
    print("ВСЕ ИМПОРТИРОВАННЫЕ ПРАВИЛА ВЫКЛЮЧЕНЫ - включай осознанно.")
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv))