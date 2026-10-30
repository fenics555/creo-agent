# -*- coding: utf-8 -*-
r"""
plm_feattype.py — СЛОВАРЬ ТИПОВ ЭЛЕМЕНТОВ Creo + чтение дерева «в лоб»

КАНОН: repo\Creo\READ\SKILL_creo_feattype_dict.md (§171)
ИСТОЧНИК СЛОВАРЯ: D:\PTC\CREO13\Creo 13.4.1.0\Common Files\otk\otk_cpp\include\pfcFeature.h
  enum pfcFeatureType { pfcFEATTYPE_FIRST, pfcFEATTYPE_HOLE, ... }  — 314 значений

ФОРМУЛА:  feat_defs_<N>  −  910  =  индекс в pfcFeatureType  →  ИМЯ ТИПА
ПОДТВЕРЖДЕНО 7/7 замером J-Link (см. §171).

Использование:
    from plm_feattype import load_dict, read_tree
    D = load_dict()                     # {1:'HOLE', 3:'ROUND', ...}
    read_tree(r"Z:\...\model.prt.1")    # список элементов: (feat_defs_N, тип, имя, id)
"""
import os
import re

# --- путь к заголовку Creo 13 (словарь) ---
_H = r"D:\PTC\CREO13\Creo 13.4.1.0\Common Files\otk\otk_cpp\include\pfcFeature.h"
# запасные пути (другие версии)
_ALT = [
    r"D:\PTC\CREO12\Creo 12.4.2.0\Common Files\otk\otk_cpp\include\pfcFeature.h",
]

_OFFSET = 910          # feat_defs_<N> − 910 = тип
_CACHE = None


def _header_path():
    for p in [_H] + _ALT:
        if os.path.exists(p):
            return p
    return None


def load_dict():
    """{индекс: ИМЯ_ТИПА} из enum pfcFeatureType. Кэшируется."""
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    p = _header_path()
    if not p:
        raise FileNotFoundError("pfcFeature.h не найден — укажи путь к Creo")
    t = open(p, encoding="utf-8", errors="replace").read()
    m = re.search(r"enum pfcFeatureType\s*\{(.*?)\}", t, re.S)
    if not m:
        raise ValueError("enum pfcFeatureType не найден в " + p)
    items = [x.strip() for x in m.group(1).split(",") if x.strip()]
    _CACHE = {i: n.replace("pfcFEATTYPE_", "") for i, n in enumerate(items)}
    return _CACHE


def read_tree(path):
    """
    Дерево элементов из .prt «в лоб» (без Creo).
    Возвращает список dict: {defs, typenum, typename, id, symbol_key}
    ВНИМАНИЕ: на 30.10.2026 это ОБЪЯВЛЕНИЯ ТИПОВ (по 1 на тип), а не полный список
    элементов. Полный список (цепочка first_feat_ptr) — открытая задача (§171).
    """
    D = load_dict()
    b = open(path, "rb").read()
    out = []
    for m in re.finditer(rb"feat_defs_(\d+)", b):
        n = int(m.group(1))
        tno = n - _OFFSET
        seg = b[m.end():m.end() + 140]
        mi = re.search(rb"id\x00(.)", seg)
        ms = re.search(rb"symbol_key\x00(.)", seg)
        out.append({
            "defs": n,
            "typenum": tno,
            "typename": D.get(tno, "?"),
            "id": mi.group(1)[0] if mi else None,
            "symbol_key": ms.group(1)[0] if ms else None,
        })
    return out


if __name__ == "__main__":
    D = load_dict()
    print(f"СЛОВАРЬ pfcFEATTYPE: {len(D)} значений (индексы {min(D)}..{max(D)})")
    for i in (0, 1, 3, 6, 7, 13, 16, 17, 21):
        print(f"  {i:>4} = {D.get(i)}")
