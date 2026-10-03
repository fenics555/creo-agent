# -*- coding: utf-8 -*-
"""ПРИЁМКА ВОЛНЫ 5 — каркас проверок и единый прогон.
Запуск: cmd /c "cd /d D:\\AI\\tools\\agent && python -X utf8 dev\\vol5_check.py"
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))

fail = []


def ok(name, cond, detail=""):
    d = detail if isinstance(detail, str) else str(detail)
    print(("OK   " if cond else "FAIL ") + name + ((" | " + d) if d else ""))
    if not cond:
        fail.append(name)


import checks as CH          # noqa: E402
import checks_tools as CT    # noqa: E402

# 1. паспорта проверок полны
need = ("id", "title", "kind", "scope", "severity")
bad_spec = [c["id"] for c in CH.CHECKS
            if any(not c.get(k) and c.get(k) != 0 for k in need) or not callable(c.get("run"))]
ok("все проверки с полным паспортом и функцией", not bad_spec,
   "проверок: %d, дефектных: %s" % (len(CH.CHECKS), bad_spec))
ok("проверок ≥ 5", len(CH.CHECKS) >= 5, "проверок: %d" % len(CH.CHECKS))

# 2. единый прогон: все проверки отработали, падение одной НЕ роняет прогон
res = CH.checks_run(as_json=True)
ok("checks_run отработал по всем проверкам", res["checks"] == len(CH.CHECKS),
   "прогнано: %d из %d" % (res["checks"], len(CH.CHECKS)))
ok("процент соответствия посчитан", res["percent"] is not None,
   "соответствие: %s" % (round(res["percent"]) if res["percent"] is not None else "н/д"))
ok("в сводке есть объекты (не пусто)", res["items"] > 0, "объектов: %d" % res["items"])

# 3. фильтр по области и по id
r1 = CH.checks_run("rules", as_json=True)
ok("фильтр по области работает", r1["checks"] == 1 and r1["rows"][0]["id"] == "rules",
   "проверок: %d" % r1["checks"])
r2 = CH.checks_run(only="hol_check,config_paths", as_json=True)
ok("фильтр по id работает", r2["checks"] == 2, "проверок: %d" % r2["checks"])

# 4. ПАДЕНИЕ ПРОВЕРКИ НЕ РОНЯЕТ ПРОГОН — главное требование каркаса
bad_spec = {"id": "boom", "title": "падающая", "kind": "check", "scope": "test",
            "severity": "error", "run": lambda: (_ for _ in ()).throw(RuntimeError("бум"))}
CH.CHECKS.append(bad_spec)
try:
    r3 = CH.checks_run(as_json=True)
    ok("упавшая проверка даёт провал, а не падение", r3["failed_checks"] == 1
       and "бум" in r3["rows"][-1]["detail"],
       "провалов: %d" % r3["failed_checks"])
finally:
    CH.CHECKS.remove(bad_spec)

# 5. отчёт пишется, один на прогон
p = CH.write_report(res)
ok("отчёт прогона записан", Path(p).exists(), p)
txt = Path(p).read_text(encoding="utf-8")
ok("в отчёте есть сводка и процент", "соответствие" in txt.lower() and "## Проверки" in txt)

# 6. рендер читаем
out = CH.render(res)
ok("рендер: есть строки проверок и вердикт",
   "СООТВЕТСТВИЕ" in out and "ВЕРДИКТ" in out and out.count("✅") >= 1)

# 7. СТАРЫЕ ПРОВЕРКИ РАБОТАЮТ И ПО-СТАРОМУ (требование плана)
import subprocess
r = subprocess.run([sys.executable, "-X", "utf8", "hol_check.py"], cwd=str(AGENT / "hol_check"),
                   capture_output=True, text=True, timeout=90)
ok("старая проверка hol_check работает по-своему (RC)", r.returncode in (0, 1),
   "RC=%d" % r.returncode)
r = subprocess.run([sys.executable, "-X", "utf8", "config_audit.py"],
                   cwd=str(AGENT / "config_audit"), capture_output=True, text=True, timeout=90)
ok("старая проверка config_audit работает по-своему", r.returncode == 0,
   "RC=%d" % r.returncode)

# 8. инструменты агента
ok("checks_list печатает реестр", "ПРОВЕРКИ ДОМА" in CT.tool_checks_list())
ok("checks_run отдаёт сводку", "ПРОГОН ПРОВЕРОК" in CT.tool_checks_run())
ok("checks_report находит отчёты", "REPORT_checks_run" in CT.tool_checks_report())

print("\n=== ИТОГ ВОЛНЫ 5: %s (провалов %d) ===" % ("ОК" if not fail else "НЕ ОК", len(fail)))
if fail:
    print("провалы: " + "; ".join(fail))
sys.exit(1 if fail else 0)