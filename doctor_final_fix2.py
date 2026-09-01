# -*- coding: utf-8 -*-
import io
from pathlib import Path

p = r"D:\AI\tools\agent\diagnostic_tools.py"
s = io.open(p, encoding="utf-8").read()
i = s.find("def tool_creoson_full_test")
if i < 0:
    print("[x] не найдена tool_creoson_full_test"); raise SystemExit
j = s.find("\ndef ", i + 10)
if j < 0: j = s.find("\nTOOLS", i + 10)

NEW = '''def tool_creoson_full_test(**kw):
    import os, re, time, pathlib
    import creo_tools as CT
    out, fails = [], []
    def rep(line, okf=True):
        out.append(line); _w(line, True)
        if not okf: fails.append(line[:70])
    act = CT.tool_get_active()
    rep("== старт, активная: %s ==" % act)
    for cmd, fn, data in [("creo", "pwd", {}), ("creo", "list_files", {"filename": "*"}),
            ("file", "list", {}), ("file", "exists", {"file": act}),
            ("file", "get_fileinfo", {"file": act}), ("file", "massprops", {"file": act}),
            ("file", "relations_get", {"file": act}), ("file", "open_errors", {"file": act}),
            ("parameter", "list", {"file": act}), ("parameter", "exists", {"file": act, "name": "ОБОЗНАЧЕНИЕ"}),
            ("dimension", "list", {"file": act}), ("feature", "list", {"file": act}),
            ("bom", "get_paths", {"file": act, "paths": False, "top_level": False, "exclude_inactive": True}),
            ("familytable", "list", {"file": act}), ("layer", "list", {"file": act}),
            ("note", "list", {"file": act}), ("view", "list", {"file": act}),
            ("geometry", "bound_box", {"file": act})]:
        jz = CT.creo_call(cmd, fn, data, 20)
        rep("чтение %-20s %s" % (cmd + ":" + fn, "OK" if CT.ok(jz) else "ERR " + str(CT.errmsg(jz))[:50]), CT.ok(jz))
    dd0 = (CT.creo_call("creo", "pwd", {}) or {}).get("data")
    orig = (dd0.get("directory") if isinstance(dd0, dict) else str(dd0 or "")) or ""
    d = str(pathlib.Path(core.BASE) / "diag_test"); os.makedirs(d, exist_ok=True)
    jl = CT.creo_call("file", "list", {})
    lst = CT._flex_list(jl.get("data")) if CT.ok(jl) else []
    src = next((x for x in lst if x.lower().endswith(".prt")), "")
    if not src:
        rep("FAIL: нет .prt в сессии для копии", False)
    else:
        base = re.sub(r"\\.prt(\\.\\d+)?$", "", src, flags=re.I)
        jb = CT.creo_call("file", "backup", {"file": src, "target_dir": d}, 30)
        rep("запись backup %s (target_dir): %s" % (src, "OK" if CT.ok(jb) else "ERR " + str(CT.errmsg(jb))[:60]), CT.ok(jb))
        jcd = CT.creo_call("creo", "cd", {"dirname": d})
        rep("запись cd diag_test: %s" % ("OK" if CT.ok(jcd) else "ERR " + str(CT.errmsg(jcd))[:50]), CT.ok(jcd))
        copy = "diagtest_%d" % int(time.time())
        cands = sorted(pathlib.Path(d).glob(base + ".prt*"), key=lambda q: q.stat().st_mtime, reverse=True)
        if cands:
            try:
                os.rename(cands[0], pathlib.Path(d) / (copy + ".prt")); rep("запись ОС-rename бэкапа в копию: OK")
            except Exception as e:
                rep("запись ОС-rename бэкапа: ERR %s" % e, False)
        else:
            rep("FAIL: бэкап не оставил файл в diag_test", False)
        jo = CT.creo_call("file", "open", {"file": copy + ".prt", "display": False}, 30)
        rep("запись open копии: %s" % ("OK" if CT.ok(jo) else "ERR " + str(CT.errmsg(jo))[:60]), CT.ok(jo))
        jps = CT.creo_call("parameter", "set", {"file": copy + ".prt", "name": "DIAG_TEST", "value": "full", "type": "STRING"}, 20)
        rep("запись parameter:set: %s" % ("OK" if CT.ok(jps) else "ERR " + str(CT.errmsg(jps))[:60]), CT.ok(jps))
        jrg = CT.creo_call("file", "regenerate", {"file": copy + ".prt"}, 30)
        rep("запись regenerate: %s" % ("OK" if CT.ok(jrg) else "ERR " + str(CT.errmsg(jrg))[:50]), CT.ok(jrg))
        jpl = CT.creo_call("parameter", "list", {"file": copy + ".prt"}, 20)
        have = []
        if CT.ok(jpl):
            dd = jpl.get("data") or {}
            have = [q2.get("name") for q2 in (dd.get("paramlist") or dd.get("param_list") or [])]
        rep("запись чтение обратно DIAG_TEST: %s" % ("DIAG_TEST" in have), "DIAG_TEST" in have)
        jsv = CT.creo_call("file", "save", {"file": copy + ".prt"}, 20)
        rep("запись save: %s" % ("OK" if CT.ok(jsv) else "ERR " + str(CT.errmsg(jsv))[:50]), CT.ok(jsv))
        je = CT.creo_call("file", "erase", {"file": copy + ".prt"}, 15)
        rep("запись erase: %s" % ("OK" if CT.ok(je) else "ERR " + str(CT.errmsg(je))[:50]), CT.ok(je))
        ren_ok = False
        for q3 in sorted(pathlib.Path(d).glob(copy + ".prt*"), key=lambda q: q.stat().st_mtime, reverse=True):
            try:
                os.rename(q3, pathlib.Path(d) / (copy + "_ren.prt")); ren_ok = True; break
            except Exception:
                pass
        rep("запись rename (ОС — правильно для async CREOSON): %s" % ("OK" if ren_ok else "ERR"), ren_ok)
        if orig:
            CT.creo_call("creo", "cd", {"dirname": orig})
        for q4 in list(pathlib.Path(d).glob("diagtest_*")) + list(pathlib.Path(d).glob(base + ".prt*")):
            try:
                q4.unlink(); _w("очистка del %s" % q4.name, True)
            except Exception:
                pass
    v = "ПРОЙДЕН" if not fails else "НЕ ПРОЙДЕН (%d): %s" % (len(fails), "; ".join(fails)[:300])
    _w("== creoson_full_test вердикт: %s" % v, True)
    return "\\n".join(out) + "\\nвердикт: %s" % v
'''
s = s[:i] + NEW + s[j:]
io.open(p, "w", encoding="utf-8").write(s)
print("[+] creoson_full_test: backup=target_dir, rename через ОС, без «предупреждений»")

ERR = """# ERR_creoson_write_ops — пишущие операции CREOSON в async-соединении
СТАТУС: ПРАВИЛО (не повторять). Выявлено 01.09.2026 полным тестом.

## backup
file:backup БЕЗ параметра target_dir → «No 'target_dir' parameter given».
ПРАВИЛЬНО: {"file": <имя>, "target_dir": <путь>}. (dirname — НЕ параметр backup.)

## rename
file:rename в async CREOSON → Pro/TOOLKIT General Error. НЕ РАБОТАТ в принципе.
ПРАВИЛЬНО: переименовывать файлы на уровне ОС (os.rename по версиям .prt.N)
либо через синхронную сессию CreoJS (схема Давыдовки: rename в сессии + save).
Для копии: backup(target_dir) → cd → open → правки → save → erase → ОС-rename.

## open после backup
open видит файл только если backup прошёл и сделан cd в ту же папку.
Проверять оба шага, иначе каскад «was not open / could not open».

## вердикты
Тест ПРОЙДЕН только если ВСЕ шаги OK. «Предупреждение» = НЕ ПРОЙДЕН.
"""
SKILL = """---
name: creoson_write_rules
system: Creo
description: Use when: пишущие операции через CREOSON (backup, rename, копия моделей)
when: creoson, backup, rename, копия, async
priority: critical
---
# CREOSON: пишущие операции (async-мост)
1. backup: только с "target_dir". Без него ошибка параметра.
2. rename: file:rename в async НЕ работает (General Error). Файлы — ОС-rename;
   сессионное переименование — только через синхронный CreoJS (J-link в Creo).
3. Копия модели: backup(target_dir=temp) → creo:cd temp → file:open →
   parameter/set, relations_set, regenerate → file:save → file:erase →
   ОС-rename/перенос файлов → creo:cd обратно.
4. Полный тест (creoson_full_test) считается ПРОЙДЕН только при всех OK;
   «предупреждений» в вердикте не бывает.
См. также: Ошибки/ERR_creoson_write_ops.md
"""
repo = Path(r"D:\AI\repo")
e = repo / "Ошибки" / "ERR_creoson_write_ops.md"
e.parent.mkdir(parents=True, exist_ok=True)
e.write_text(ERR, encoding="utf-8")
print("[+] правило в ОШИБКИ:", e)
k = repo / "Creo" / "SKILL_creoson_write_rules.md"
k.parent.mkdir(parents=True, exist_ok=True)
k.write_text(SKILL, encoding="utf-8")
print("[+] правило в репозиторий:", k)
print("ТЕПЕРЬ: .\\AI_RESTART.bat, затем creoson_full_test, затем GIT_SYNC")