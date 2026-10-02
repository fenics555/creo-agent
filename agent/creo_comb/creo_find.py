# -*- coding: utf-8 -*-
r"""creo_find.py — ГДЕ ВЗЯТЬ CREO (источник истины, 02.10.2026).

Проблема, которую он снимает: путь к Creo был зашит в `creo_comb.bat` как
`D:\PTC\CREO12\Creo 12.4.2.0\Common Files`, а дом с 2026 года работает на CREO13.
Завтра будет CREO14 — и зашитый путь снова станет неправдой.

ПРИОРИТЕТ ИСТОЧНИКОВ (правило из SKILL_audit_program п.10, грабли 10.1–10.3):
  1) БАТ ЗАПУСКА `Z:\PTC\CREO-START\START-STD\CREO-START.bat` (`set CREO_EXE=…`) —
     чем дом РЕАЛЬНО стартует. Это главный источник.
  2) Настройки `data\\creo_comb_settings.json` → `creo_common` (если заданы и живы).
  3) Автопоиск на диске `D:\\PTC\\CREO*\\Creo *\\Common Files` — берётся установка,
     у которой ЕСТЬ `x86e_win64\\lib` (признак рабочей, а не огрызка).

Печатает в stdout путь Common Files (без кавычек) или пустую строку.
"""
import json
import os
import re
import sys

START_BATS = (r"Z:\PTC\CREO-START\START-STD\CREO-START.bat",
              r"Z:\PTC\CREO-START\START-Config\CREO-START.bat")
PTC_ROOT = r"D:\PTC"
SETTINGS = r"D:\AI\tools\agent\data\creo_comb_settings.json"


def _ok(common_files):
    """Рабочая установка = есть x86e_win64\\lib (там живут pro_comm_msg и lib)."""
    return bool(common_files) and os.path.isdir(os.path.join(common_files, "x86e_win64", "lib"))


def from_launcher():
    """1) Путь из боевого бата запуска."""
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
        # ...\Creo 13.4.1.0\Parametric\bin\parametric.exe -> ...\Creo 13.4.1.0\Common Files
        parametric = os.path.dirname(os.path.dirname(exe))
        root = os.path.dirname(parametric)          # ...\Creo 13.4.1.0
        com = os.path.join(root, "Common Files")
        if _ok(com):
            return com, "бат запуска %s" % os.path.basename(bat)
    return None, "в бате запуска CREO_EXE не найден"


def from_settings():
    """2) Явно заданный путь (если владелец его задал)."""
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            com = (json.load(f) or {}).get("creo_common")
        if com and _ok(com):
            return com, "настройки %s" % SETTINGS
    except Exception:
        pass
    return None, "в настройках нет"


def from_disk():
    """3) Автопоиск: новейшая установка с признаком рабочей."""
    found = []
    try:
        fams = sorted(os.listdir(PTC_ROOT), reverse=True)
    except OSError:
        return None, "нет %s" % PTC_ROOT
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
            if _ok(com):
                found.append((com, "%s\\%s" % (fam, v)))
    if found:
        return found[0][0], "поиск на диске: %s" % found[0][1]
    return None, "на диске не найдено ни одной рабочей установки"


def find(verbose=False):
    for fn in (from_launcher, from_settings, from_disk):
        com, why = fn()
        if com:
            if verbose:
                sys.stderr.write("creo_find: %s <- %s\n" % (com, why))
            return com, why
    return None, "источник не найден"


if __name__ == "__main__":
    com, why = find(verbose=("-v" in sys.argv))
    print(com or "")