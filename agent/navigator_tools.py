# -*- coding: utf-8 -*-
"""navigator_tools — НАВИГАТОР в диалоге агента (класс Р, только чтение индекса дома).

Зачем: чтобы в окне агента можно было просто написать «найди сборки турноверов»,
получить список, выбрать сборку и сразу увидеть деталировку — а окно навигатора открыть на выбранном.

Инструменты:
  nav_find  q=<слова>      — поиск по домашнему индексу (имя и путь), вернёт список групп
  nav_bom   q=<сборка>     — деталировка сборки из индекса (позиции, количество, есть ли PDF)
  nav_show  q=<сборка>     — открыть окно НАВИГАТОРА на этой сборке (окно само покажет деталировку и PDF)

Пишущих операций нет: чужой индекс читается только на чтение.
"""
import os
import subprocess
import sys
from pathlib import Path

NAV_DIR = Path(r"D:\AI\tools\agent\navigator")
if str(NAV_DIR) not in sys.path:
    sys.path.insert(0, str(NAV_DIR))
import navigator as NAV  # noqa: E402


def tool_nav_find(q="", only_asm=False, limit=40, **kw):
    if not q or len(str(q).strip()) < 2:
        return "укажи хотя бы 2 буквы: nav_find q=турновер"
    res = NAV.find(str(q), limit=int(limit) or 40, only_asm=bool(only_asm))
    if not res:
        return "ничего не найдено по «%s». Попробуй иначе: turn / турн / поворот (поиск идёт и по путям папок)" % q
    asm = [r for r in res if r["kind"] == "сборка"]
    other = [r for r in res if r["kind"] != "сборка"]
    out = ["НАЙДЕНО по «%s»: %d (сборок %d, прочего %d)" % (q, len(res), len(asm), len(other))]
    if asm:
        out.append("сборки (выбери и скажи nav_bom q=<имя>):")
        for r in asm[:20]:
            out.append("   %-38s %s" % (r["name"], r["folder"]))
    if other:
        out.append("прочее (первые 5):")
        for r in other[:5]:
            out.append("   %-38s %s" % (r["name"], r["folder"]))
    out.append("подсказка: nav_show q=<имя сборки> откроет окно навигатора сразу на ней")
    return "\n".join(out)


def tool_nav_bom(q="", depth=2, **kw):
    if not q:
        return "укажи сборку: nav_bom q=<имя сборки>"
    name = str(q).strip()
    if not name.lower().endswith((".1", ".2", ".3")):
        name = name + ".1"
    rows = NAV.bom(name, depth=int(depth) or 2)
    if not rows:
        return ("состава в индексе нет для «%s». Возможные причины: модель не проиндексирована "
                "(помогает ночной скан) или это не сборка." % name)
    withpdf = sum(1 for r in rows if r["has_pdf"])
    out = ["ДЕТАЛИРОВКА %s: позиций %d (с PDF %d) — глубина %s:" % (name, len(rows), withpdf, depth)]
    for n, r in enumerate(rows[:40], 1):
        out.append("   %2d) %-8s %-36s кол-во %-4s %s" % (n, r["kind"], r["name"], r["qty"],
                                                           "PDF: " + os.path.basename(r["pdf"]) if r["has_pdf"] else "PDF нет"))
    if len(rows) > 40:
        out.append("   … и ещё %d позиций (nav_show покажет все)" % (len(rows) - 40))
    return "\n".join(out)


def tool_nav_show(q="", **kw):
    """Открыть окно НАВИГАТОРА на нужной сборке: окно покажет деталировку и PDF по клику."""
    bat = NAV_DIR / "navigator_gui.bat"
    if not bat.exists():
        return "окно навигатора не найдено: %s" % bat
    try:
        env = dict(os.environ)
        env["NAV_START_QUERY"] = str(q or "")
        subprocess.Popen(["cmd", "/c", str(bat)], cwd=str(NAV_DIR), env=env)
        return "открыл окно НАВИГАТОРА (запрос: %s). В окне слева список — выбирай сборку, справа появится деталировка, внизу PDF." % (q or "—")
    except Exception as e:
        return "не открыть окно: %s" % e


TOOLS = [
    {"name": "nav_find", "desc": "Найти сборки/детали/чертежи по словам (индекс дома, и по путям папок)",
     "params": {"q": "слова", "only_asm": "true — только сборки", "limit": "сколько показать"},
     "approval": False, "fn": tool_nav_find},
    {"name": "nav_bom", "desc": "Деталировка сборки из индекса дома (позиции, количество, есть ли PDF)",
     "params": {"q": "сборка", "depth": "глубина (1-2)"},
     "approval": False, "fn": tool_nav_bom},
    {"name": "nav_show", "desc": "Открыть окно НАВИГАТОРА на сборке: деталировка + PDF с увеличением",
     "params": {"q": "сборка"}, "approval": False, "fn": tool_nav_show},
]