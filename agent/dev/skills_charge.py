# -*- coding: utf-8 -*-
r"""ЗАРЯД ЗНАНИЙ АГЕНТА (dev\skills_charge.py)

Зачем: раньше база знаний грузилась в РАМ целиком (16 ГБ), и агент «уже знал» всё.
Теперь память — FTS5-поиск, поэтому на старт нужна КАРТА скиллов (что у него есть)
плюс СТАРТОВЫЙ НАБОР текстов, которые он читает сразу.

Делает два файла в репо (D:\AI\repo):
  SKILL_CHARGE.md        — карта: каждый скилл одной строкой (домен → путь → когда брать)
  SKILL_CHARGE_START.md  — стартовый набор: полные тексты главных скиллов Creo/CREOSON

Запуск:  python dev\skills_charge.py            (пересобрать)
         python dev\skills_charge.py --show     (только показать цифры, не писать)

Правило дома: агент читает эти файлы через loop.build_system (режим ИНЖЕНЕРА).
"""
import sys, re, datetime
from pathlib import Path

REPO = Path(r"D:\AI\repo")
OUT_MAP = REPO / "SKILL_CHARGE.md"
OUT_START = REPO / "SKILL_CHARGE_START.md"
SHOW = "--show" in sys.argv

# Стартовый набор: читать ВСЕГДА и сразу (порядок = приоритет).
# Главное направление дома — CREO, поэтому сначала индекс Creo и CREOSON.
START_SET = [
    "Creo\\SKILL_creo_index.md",
    "Creo\\CREOSON\\_INDEX.md",
    "Creo\\CREOSON\\SKILL_creoson_workflow.md",
    "Creo\\STANDARDS\\SKILL_creo_model_nature.md",
    "SKILL_index.md",
]
# Домены, которые агент должен видеть как «своё» (порядок в карте)
DOMAIN_ORDER = ["Creo", "PDF", "PLM", "Web", "Инженерные", "Трейлы", "Ошибки", "crash",
                "Skills", "Prog", "Память", "Дом", "Прочее"]
KEY_LIMITS = (80, 110)  # (когда брать, описание) — обрезка строк в карте


def read_text(p):
    """utf-8-sig, при осечке — cp1251 (живая находка дома: файлы часто из PowerShell)."""
    for enc in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            return p.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
        except Exception:
            return ""
    return p.read_text(encoding="utf-8", errors="replace")


def front_matter(txt):
    """Шапка скилла = ведущие строки вида `ключ: значение` (бывает и без --- каёмки)."""
    fm, started = {}, False
    for line in txt.splitlines()[:40]:
        s = line.strip()
        if not s:
            if started:
                break
            continue
        if s in ("---", "==="):
            started = True
            continue
        m = re.match(r"^([A-Za-zА-Яа-я_][\w\- ]{1,24}):\s*(.+)$", s)
        if m:
            fm[m.group(1).strip().lower()] = m.group(2).strip()
            started = True
            continue
        if started:
            break
    return fm


def cut(s, n):
    s = re.sub(r"\s+", " ", (s or "")).strip()
    return s if len(s) <= n else s[: n - 1].rstrip(" ,.;:-") + "…"


def collect():
    """Все скиллы репо: (относительный путь, шапка, размер)."""
    items = []
    for p in sorted(REPO.rglob("*.md")):
        low = p.name.lower()
        if not (low.startswith("skill_") or low == "_index.md" or low.startswith("err_") or low.startswith("crash_")):
            continue
        if "_charge" in low or p.parent.name == "backup_db":
            continue
        rel = p.relative_to(REPO)
        items.append((str(rel), front_matter(read_text(p)), p.stat().st_size))
    return items


def domain_of(rel):
    top = rel.split("\\")[0]
    if top.endswith(".md"):
        return "Прочее"
    return top if top in DOMAIN_ORDER else "Прочее"


def main():
    items = collect()
    by_domain = {}
    for rel, fm, size in items:
        by_domain.setdefault(domain_of(rel), []).append((rel, fm, size))

    now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    lines = [
        "---",
        "name: CHARGE",
        "system: ЗНАНИЯ",
        "description: Use when: карта скиллов репо — что есть и когда брать (сборка dev\\skills_charge.py)",
        "when: карта скиллов, заряд знаний, какие скиллы есть, индекс скиллов",
        "date: %s" % now,
        "---",
        "",
        "# ЗАРЯД ЗНАНИЙ АГЕНТА (карта скиллов репо)",
        "",
        "**Собрано:** %s · скиллов: %d" % (now, len(items)),
        "",
        "**Как этим пользоваться (агенту).** Это КАРТА: здесь каждый скилл одной строкой — «что это и когда брать».",
        "Тела скиллов в промпт не грузятся: нужный открывается `search_kb` (поиск) или `read_file` (по пути).",
        "Начинать любую задачу Creo — со стартового набора `SKILL_CHARGE_START.md` (он уже в промпте).",
        "Главное направление дома — **Creo/CREOSON**.",
        "",
    ]
    for dom in DOMAIN_ORDER:
        rows = by_domain.get(dom)
        if not rows:
            continue
        lines.append("## %s (%d)" % (dom, len(rows)))
        for rel, fm, size in rows:
            when = cut(fm.get("when") or fm.get("description") or fm.get("name") or "", KEY_LIMITS[0])
            desc = cut(fm.get("description") or fm.get("system") or "", KEY_LIMITS[1])
            tail = (" · когда: " + when) if when else ""
            lines.append("- `%s` — %s%s" % (rel, desc or "(без описания)", tail))
        lines.append("")
    map_text = "\n".join(lines)

    start_parts = [
        "---",
        "name: CHARGE_START",
        "system: ЗНАНИЯ",
        "description: Use when: стартовый набор знаний Creo/CREOSON — полные тексты главных скиллов (уже в промпте агента)",
        "when: стартовый набор, Creo, CREOSON, с чего начать задачу, индекс Creo",
        "date: %s" % now,
        "---",
        "",
        "# СТАРТОВЫЙ НАБОР ЗНАНИЙ (читать сразу, это в промпте агента)",
        "",
        "**Собрано:** %s" % now,
        "Порядок чтения: индекс Creo → индекс CREOSON → рутина CREOSON → природа модели → общая карта скиллов.",
        "",
    ]
    used = []
    for rel in START_SET:
        p = REPO / rel
        if not p.exists():
            start_parts.append("## %s — НЕТ ФАЙЛА" % rel)
            continue
        txt = read_text(p)
        used.append("%s (%d КБ)" % (rel, round(len(txt.encode("utf-8")) / 1024, 1)))
        start_parts.append("\n\n===== %s =====\n%s" % (rel, txt.strip()))
    start_text = "\n".join(start_parts)

    print("скиллов найдено: %d" % len(items))
    print("карта: %d КБ" % round(len(map_text.encode('utf-8')) / 1024, 1))
    print("стартовый набор: %d КБ — %s" % (round(len(start_text.encode('utf-8')) / 1024, 1), "; ".join(used)))
    if SHOW:
        print("режим --show: файлы не пишу")
        return
    OUT_MAP.write_text(map_text, encoding="utf-8", newline="\n")
    OUT_START.write_text(start_text, encoding="utf-8", newline="\n")
    print("записано: %s" % OUT_MAP)
    print("записано: %s" % OUT_START)


main()
