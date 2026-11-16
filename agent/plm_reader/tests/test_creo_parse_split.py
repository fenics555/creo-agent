# -*- coding: utf-8 -*-
"""Регресс-тест V201: парсеры Creo вынесены в plm_creo_parse, engine реэкспортирует."""
import os
import sys

HERE = r"D:\AI\tools\agent\plm_reader"
sys.path.insert(0, HERE)
os.chdir(HERE)
import engine as E              # noqa: E402
import plm_creo_parse as CP     # noqa: E402

fails = []


def check(name, got, want):
    ok = (got == want)
    print("%-46s %-6s got=%r" % (name, "OK" if ok else "FAIL", got))
    if not ok:
        fails.append(name)


for fn in ("creo_params", "family_of", "creo_history", "creo_mass_props", "creo_dimensions",
           "creo_features", "creo_equations", "creo_materials", "creo_health"):
    check("%s.__module__" % fn, getattr(E, fn).__module__, "plm_creo_parse")
check("_creo_clean is CP", E._creo_clean is CP._creo_clean, True)
check("_e32_decode is CP", E._e32_decode is CP._e32_decode, True)
check("CREO_TYPES is CP", E.CREO_TYPES is CP.CREO_TYPES, True)
check("_RX_PARAM is CP", E._RX_PARAM is CP._RX_PARAM, True)
check("_creo_clean('')", E._creo_clean(""), "")
check("_e32_decode -> list", isinstance(E._e32_decode(b""), list), True)

print("")
print("ИТОГ: " + ("ВСЁ ОК" if not fails else "ПРОВАЛЫ: " + ", ".join(fails)))
sys.exit(1 if fails else 0)
