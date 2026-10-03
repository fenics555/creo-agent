# -*- coding: utf-8 -*-
r"""creo_path.py — ОБЩИЙ ПОИСК УСТАНОВКИ CREO ДЛЯ ВСЕХ ИНСТРУМЕНТОВ ДОМА (02.10.2026).

Проблема, которую он снимает: путь к Creo был зашит в `creo_comb.bat` (CREO12) и в
`creo_pdf_env.py` (только реестр), а дом с 2026 года работает на CREO13, дальше будет CREO14.

ПРИОРИТЕТ ИСТОЧНИКОВ (по надёжности — сверху вниз):
  1) БАТ ЗАПУСКА `Z:\PTC\CREO-START\...\CREO-START.bat` (`set CREO_EXE=…`) — чем дом
     РЕАЛЬНО стартует Creo. Знает только дом.
  2) РЕЕСТР `HKLM\SOFTWARE\PTC\PTC Creo Parametric` — куда Creo прописывает себя сам.
     Знает только Creo. (это то, что уже умел `creo_pdf_env.py`)
  3) ДИСК `D:\PTC\CREO*\Creo *\Common Files` с признаком рабочей установки `x86e_win64\lib`.
  4) НАСТРОЙКИ — ручной затыкающий путь.

Ничего не меняет, только читает. API:
  find()          -> (creo_common, parametric, source_where)
  common_only()   -> строка пути (пустая строка, если не нашли)
  to_set_lines()  -> ['set "CREO_COMMON=..."', 'set "CREO_PARAMETRIC=..."'] (для bat)
"""
import json
import os
import re
import subprocess

START_BATS = (r"Z:\PTC\CREO-START\START-STD\CREO-START.bat",
              r"Z:\PTC\CREO-START\START-Config\CREO-START.bat")
PTC_ROOT = r"D:\PTC"
REG_KEY = r"HKLM\SOFTWARE\PTC\PTC Creo Parametric"
SETTINGS_HINT = ("D:\\AI\\tools\\agent\\data\\creo_common.json",
                 "D:\\AI\\tools\\agent\\creo_pdf\\settings\\creo_pdf_settings.json")


def _alive(common_files):
    r"""Рабочая установка = есть x86e_win64\lib (там pro_comm_msg и lib)."""
    return bool(common_files) and os.path.isdir(os.path.join(common_files, "x86e_win64", "lib"))


def _from_launcher():
    r"""1) Бат запуска: CREO_EXE=...\Creo <верс>\Parametric\bin\parametric.exe"""
    for bat in START_BATS:
        try:
            if not os.path.isfile(bat):
                continue
            text = open(bat, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        m = re.search(r"CREO_EXE\s*=\s*([^\r\n]+)", text)
        if not m:
            continue
        exe = m.group(1).strip().strip('"')
        parametric = os.path.dirname(os.path.dirname(exe))     # ...\Creo X\Parametric
        com = os.path.join(os.path.dirname(parametric), "Common Files")
        if _alive(com):
            return com, parametric, "бат запуска %s" % os.path.basename(bat)
    return None, None, "в бате запуска CREO_EXE нет"


def _from_registry():
    """2) Реестр PTC (то, что умел creo_pdf_env.py)."""
    try:
        p = subprocess.run(["reg", "query", REG_KEY, "/s"],
                           capture_output=True, text=True, timeout=20)
        out = p.stdout or ""
    except Exception:
        return None, None, "реестр не прочитан"
    best = None
    for m in re.finditer(r"(PROE?_?INSTALL\w*|INSTDIR|INSTALLDIR)\s+REG_SZ\s+(.+)", out, re.I):
        val = m.group(2).strip()
        val = os.path.dirname(val) if val.lower().endswith((".exe", ".bat")) else val
        for cand in (val, os.path.join(val, "Common Files")):
            if _alive(cand):
                parametric = os.path.join(val, "Parametric")
                return cand, (parametric if os.path.isdir(parametric) else None), "реестр PTC"
        if best is None and os.path.isdir(val):
            best = val
    if best:
        return (os.path.join(best, "Common Files") if _alive(os.path.join(best, "Common Files"))
                else None), None, "реестр PTC (без Common Files)"
    return None, None, "в реестре PTC нет установки"


def _from_disk():
    """3) Диск: новейшая рабочая установка в D:\\PTC\\CREO*."""
    found = []
    try:
        fams = sorted(os.listdir(PTC_ROOT), reverse=True)
    except OSError:
        return None, None, "нет %s" % PTC_ROOT
    for fam in fams:
        if not fam.upper().startswith("CREO"):
            continue
        base = os.path.join(PTC_ROOT, fam)
        if not os.path.isdir(base):
            continue
        try:
            vers = sorted(os.listdir(base), reverse=True)
        except OSError:
            continue
        for v in vers:
            com = os.path.join(base, v, "Common Files")
            if _alive(com):
                found.append((com, os.path.join(base, v, "Parametric")))
    if found:
        return found[0][0], found[0][1], "поиск на диске"
    return None, None, "на диске рабочих установок нет"


def _from_settings():
    """4) Настройки — если кто-то задал руками."""
    for path in SETTINGS_HINT:
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f) or {}
            com = d.get("creo_common")
            if com and _alive(com):
                return com, d.get("creo_install"), "настройки %s" % os.path.basename(path)
        except Exception:
            continue
    return None, None, "в настройках нет"


def find():
    """Возвращает (common_files, parametric, откуда). Первый доказанный источник."""
    for fn in (_from_launcher, _from_registry, _from_disk, _from_settings):
        try:
            com, par, why = fn()
        except Exception as e:
            com, par, why = None, None, "сбой источника: %s" % e
        if com:
            return com, par, why
    return None, None, "Creo не найден"


def common_only():
    com, _par, _why = find()
    return com or ""


def to_set_lines():
    com, par, _why = find()
    if not com:
        return []
    lines = ['set "CREO_COMMON=%s"' % com]
    if par:
        lines.append('set "CREO_PARAMETRIC=%s"' % par)
    return lines


if __name__ == "__main__":
    com, par, why = find()
    print(com or "")
    if "-v" in __import__("sys").argv:
        import sys as _s
        _s.stderr.write("creo_path: %s (%s) | parametric=%s\n" % (com, why, par))