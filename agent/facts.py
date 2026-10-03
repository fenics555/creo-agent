# -*- coding: utf-8 -*-
r"""facts.py — СБОР ФАКТОВ ИЗ МОДЕЛИ для движка правил (закрытие долга волн 4–5).

Проблема была: правила написаны, движок работает, а факты брались только демонстрационные.
Здесь факты берутся из ЖИВЫХ файлов Creo БЕЗ самого Creo — читателем `creo_read.py`
(домашняя библиотека, класс Р).

ЖИВАЯ ПРОВЕ��КА (03.10.2026): файл
`Z:\PTC\CREO-START\Libraries\Библиотека_стандартных_изделий\Болты_винты\g11074.prt.1`
→ **194 параметра**, среди них `NAME_1='Винт'`, `NAME_2='ГОСТ 11074-93'`, `STANDART`,
`GROUP='std'`, `ТИП='Стандарт'`.

ЧТО ДЕЛАЕТ ФАКТ: превращает параметры модели в плоский список объектов для `rules_engine`:
    {"item_name": "Винт", "parameter": "STANDART", "param_value": "GOST 11074-93",
     "feature": "PRT", "component": "g11074", "group": "std", "feat_type": "PARAM"}
Правила, написанные под признаки модели (резьба, диаметр, ползун), сработают, когда
модель содержит такие параметры; не содержит — правило честно молчит.
"""
import os
import sys
from pathlib import Path

AGENT = Path(__file__).resolve().parent
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

import creo_read as CR   # noqa: E402


def model_path(name="", root=None):
    """Ищет файл модели по коду изделия: версия .1 приоритетнее, потом .prt/.asm.

    ВНИМАНИЕ: pathlib.rglob сравнивает РЕГИСТР строго, а файлы Creo лежат в нижнем
    регистре (`g11074.prt.1`) — поэтому поиск идёт через os.walk со сверкой вниз.
    Это найдено живой пробой 03.10.2026: rglob вернул пусто при существующем файле."""
    stem = (CR.stem(name) if name else "").lower()
    if not stem:
        return None
    roots = [Path(root)] if root else [Path(r"Z:\PTC\CREO-START\Libraries"),
                                        Path(r"Z:\PTC\Work")]
    want = [stem + ".prt.1", stem + ".asm.1", stem + ".prt", stem + ".asm"]
    best = None
    for r in roots:
        if not r.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(str(r)):
            low = [f.lower() for f in filenames]
            for w in want:
                if w in low:
                    hit = os.path.join(dirpath, filenames[low.index(w)])
                    if w.endswith(".1"):          # версия приоритетнее
                        return hit
                    best = best or hit
            if len(dirpath) > 400 and best:      # уже нашли — дальше не лезем
                break
    return best


def facts_from_file(path):
    """Параметры одного файла модели → список объектов-фактов для движка правил."""
    raw = CR.read(str(path))
    toc = CR.parse_toc(raw)
    params = CR.params(raw, toc) or {}
    name = Path(path).name
    comp = CR.stem(name)
    out = []
    for pname, pval in params.items():
        out.append({"item_name": params.get("NAME_1") or comp,
                    "parameter": pname,
                    "param_value": pval,
                    "feature": Path(name).suffix.upper().lstrip("."),
                    "feat_type": "PARAM",
                    "group": params.get("GROUP") or "",
                    "component": comp,
                    "source_file": str(path)})
    return out, len(params)


def collect(name="", root=None, limit=400):
    """Собирает факты по изделию. Возвращает (список фактов, сводка)."""
    p = model_path(name, root)
    if p is None:
        return [], {"error": "файл модели не найден по «%s»" % (name or "пусто"),
                    "searched": [str(x) for x in ([Path(root)] if root else
                                                  [Path(r"Z:\PTC\CREO-START\Libraries"),
                                                   Path(r"Z:\PTC\Work")])]}
    try:
        facts, n = facts_from_file(p)
    except Exception as e:
        return [], {"error": "не читается %s: %s" % (p, e)}
    if not facts:
        return [], {"error": "параметров не найдено: %s" % p}
    return facts[:limit], {"file": str(p), "params": n, "facts": len(facts[:limit])}


if __name__ == "__main__":
    sys.stdout = sys.stdout if hasattr(sys.stdout, "write") else sys.stdout
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    q = sys.argv[1] if len(sys.argv) > 1 else "G11074"
    facts, info = collect(q)
    print("СБОР ФАКТОВ по «%s»: %s" % (q, info))
    for f in facts[:10]:
        print("  %-22s = %s" % (f["parameter"], str(f["param_value"])[:60]))