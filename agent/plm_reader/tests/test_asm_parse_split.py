# -*- coding: utf-8 -*-
"""Регресс-тест V200: парсеры сборки вынесены в plm_asm_parse, engine их реэкспортирует."""
import os
import sys

HERE = r"D:\AI\tools\agent\plm_reader"
sys.path.insert(0, HERE)
os.chdir(HERE)
import engine as E              # noqa: E402
import plm_asm_parse as A       # noqa: E402

fails = []


def check(name, got, want):
    ok = (got == want)
    print("%-46s %-6s got=%r" % (name, "OK" if ok else "FAIL", got))
    if not ok:
        fails.append(name)


check("engine.asm_components is plm_asm_parse", E.asm_components is A.asm_components, True)
check("engine._hash_like exists", callable(E._hash_like), True)
check("engine._internal_id exists", callable(E._internal_id), True)
check("engine.P_ASM_COMP exists", E.P_ASM_COMP is A.P_ASM_COMP, True)
check("engine.ASM_SERVICE exists", E.ASM_SERVICE is A.ASM_SERVICE, True)
check("_hash_like(hex28)", E._hash_like("0123456789ABCDEF0123456789AB"), True)
check("_hash_like('DIN912')", E._hash_like("DIN912"), False)
check("_internal_id(base36)", E._internal_id("848HJNI4L5H6O4AV25BMF289G2"), True)
check("asm_components(b'')", E.asm_components(b""), [])

print("")
print("ИТОГ: " + ("ВСЁ ОК" if not fails else "ПРОВАЛЫ: " + ", ".join(fails)))
sys.exit(1 if fails else 0)
