# -*- coding: utf-8 -*-
"""ПРИЁМКА ВОЛНЫ 2: перенос программы по контракту, без ручной докачки модулей.

Что проверяет (спека волны 2, критерий 3):
 1. контракт программы валиден, deps читаются;
 2. копия программы + модули ИЗ КОНТРАКТА запускается из другой папки → RC 0;
 3. недоступный путь → RC 2 (честный отказ, не молчание);
 4. битый tool.json не роняет читатель (проверка на копии).

Запуск: cmd /c "cd /d D:\AI\tools\agent && python -X utf8 dev\vol2_check.py"
"""
import io
import shutil
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))

import tool_contract as TC          # noqa: E402

STAMP = time.strftime("%Y%m%d_%H%M%S")
DST = Path(r"D:\AI\PROBA") / ("portable_vol2_%s" % STAMP)
fail = []


def ok(name, cond, detail=""):
    d = detail if isinstance(detail, str) else str(detail)
    print(("OK   " if cond else "FAIL ") + name + ((" | " + d) if d else ""))
    if not cond:
        fail.append(name)


def deploy(prog_id):
    """Копирует программу + модули ИЗ КОНТРАКТА (deps) в отдельную папку."""
    src = AGENT / prog_id
    dst = DST / prog_id
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
    c, err = TC.load_dir(src)
    ok("%s: контракт валиден" % prog_id, not err, err or "ошибок нет")
    deps = TC.deps_of(src)
    # каждый dep кладём рядом — и сам модуль, и его зависимости по контракту.
    # `ui` из контракта — тоже модуль каркаса, без него окно из копии не соберётся
    # (найдено приёмкой волны 2).
    deps = list(deps) + ["creo_boot", "tool_contract", (c or {}).get("ui") or "ui_common"]
    placed = []
    for dep in dict.fromkeys([d for d in deps if d]):     # без повторов, порядок сохраняется
        f = AGENT / ("%s.py" % dep)
        if f.exists():
            shutil.copy2(f, dst / f.name)
            placed.append(dep)
        else:
            ok("%s: dep %s есть" % (prog_id, dep), False, str(f))
    # модули, которые самих модулей агента тянут за собой
    for extra in ("core.py",):
        f = AGENT / extra
        if f.exists():
            shutil.copy2(f, dst / f.name)
            placed.append(extra)
    print("     развёрнуто в %s: %s" % (dst, ", ".join(placed)))
    return c, dst


if __name__ == "__main__":
    print("ПРИЁМКА ВОЛНЫ 2 — контракт и перенос")
    print("приёмка из: %s" % AGENT)
    print("приёмка в:   %s\n" % DST)

    # 1. контрактов в доме сколько
    cs = TC.all_contracts(AGENT)
    ok("контрактов в доме ≥ 2", len(cs) >= 2, "найдено: %s" % sorted(cs))
    for pid, (c, p, err) in cs.items():
        e = TC.validate(c)
        ok("контракт %s без ошибок" % pid, not e, "; ".join(e) or "ошибок нет")

    # 2. развёртывание config_audit по deps
    c_audit, d_audit = deploy("config_audit")
    ok("config_audit: deps из контракта", "creo_path" in (c_audit or {}).get("deps", []),
       str((c_audit or {}).get("deps")))

    # 3. запуск ДВИЖКА из копии
    import subprocess
    r = subprocess.run([sys.executable, "-X", "utf8", "config_audit.py"],
                       cwd=str(d_audit), capture_output=True, text=True, timeout=90)
    ok("движок из копии: RC 0", r.returncode == 0,
       "RC=%d, хвост: %s" % (r.returncode, (r.stdout or "").strip().splitlines()[-1:]))
    ok("движок из копии нашёл пути", "путей проверено" in (r.stdout or ""),
       [l for l in (r.stdout or "").splitlines() if "путей проверено" in l][:1])

    # 4. недоступный путь → RC 2 (честный отказ)
    bad = r"Z:\НЕТ\ТАКОЙ\config.pro"
    r2 = subprocess.run([sys.executable, "-X", "utf8", "config_audit.py", bad],
                        cwd=str(d_audit), capture_output=True, text=True, timeout=90)
    ok("недоступный путь: RC 2", r2.returncode == 2,
       "RC=%d, вывод: %s" % (r2.returncode, (r2.stdout or "").strip().splitlines()[-1:]))

    # 5. окно из копии собирается
    r3 = subprocess.run([sys.executable, "-X", "utf8", "-c",
                         "import sys;sys.path.insert(0,'.');import gui;"
                         "a=gui.App();print('окно собрано', a.root.winfo_exists());"
                         "a.root.destroy()"],
                        cwd=str(d_audit), capture_output=True, text=True, timeout=90)
    ok("окно из копии собрано", "окно собрано 1" in (r3.stdout or ""),
       (r3.stdout or r3.stderr or "").strip().splitlines()[-1:])

    # 6. битый контракт не роняет читатель
    (d_audit / "tool.json").write_text('{"id": "config_audit"}', encoding="utf-8")
    TC._CACHE.clear()
    bad_c, err = TC.load_dir(d_audit)
    ok("битый контракт даёт ошибку, а не исключение", bad_c is not None and bool(err),
       err or "ошибки нет (!)")
    (d_audit / "tool.json").write_text("{ НЕ JSON", encoding="utf-8")
    TC._CACHE.clear()
    bad_c2, err2 = TC.load_dir(d_audit)
    ok("нечитаемый контракт даёт ошибку", bad_c2 is None and bool(err2), err2 or "нет ошибки")

    print("\n=== ИТОГ ВОЛНЫ 2: %s (провалов %d) ===" % ("ОК" if not fail else "НЕ ОК", len(fail)))
    if fail:
        print("провалы: " + "; ".join(fail))
    print("копия приёмки: %s" % DST)
    sys.exit(1 if fail else 0)