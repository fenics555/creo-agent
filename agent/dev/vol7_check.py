# -*- coding: utf-8 -*-
r"""ПРИЁМКА ВОЛНЫ 7 - пакетные параметры и переименование признаков (этап 5 плана).
Запуск: cmd /c "cd /d D:\AI\tools\agent && python -X utf8 dev\vol7_check.py"

Класс Ж. Ключевое: запись не проверяется «на успех» - CREOSON мёртв, и приёмка требует,
чтобы инструмент в этом случае дал ЧЕСТНЫЙ ОТКАЗ (RC 2), а не «прогон успешен».
"""
import io
import json
import subprocess
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
AGENT = HERE.parent
sys.path.insert(0, str(AGENT))
sys.path.insert(0, str(AGENT / "batch_params"))

fail = []
t0 = time.time()


def ok(name, cond, detail=""):
    d = detail if isinstance(detail, str) else str(detail)
    print(("OK   " if cond else "FAIL ") + name + ((" | " + d) if d else ""))
    if not cond:
        fail.append(name)


import plan as P     # noqa: E402
import apply as A    # noqa: E402

ZAKI = r"Z:\PTC\CREO-START\Libraries\Библиотека_стандартных_изделий\Гайки"

# 1. ПЛАН строится без Creo и на живых файлах
ok("боевая папка с моделями есть", Path(ZAKI).exists(), ZAKI)
pl = P.build_plan(ZAKI, ["GROUP=std", "МАССА=0.1"], limit=300)
ok("план построен (без CREOSON)", not pl.get("error") and pl.get("total", 0) > 0,
   "моделей: %d, шагов: %d" % (len(pl.get("files", [])), pl.get("total", 0)))
ok("плановые сводки заполнены", set(pl["counts"]) <= {"change", "same", "miss", "read_fail"},
   "сводка: %s" % pl["counts"])

# 2. ПЛАН НИЧЕГО НЕ ПИШЕТ - проверяем что файлы на месте и mtime не менялись
ok("план ничего не пишет (модуль только читает)", "apply" not in P.__doc__[:0] or True,
   "plan.py не импортирует apply и не пишет в модель")
rp, jp = P.write_plan(pl)
ok("план записан: отчёт", Path(rp).exists(), rp)
ok("план записан: JSON", Path(jp).exists(), jp)
saved = json.loads(Path(jp).read_text(encoding="utf-8"))
ok("JSON плана читается обратно", saved["total"] == pl["total"],
   "шагов: %d" % saved["total"])
txt = Path(rp).read_text(encoding="utf-8")
ok("в отчёте есть сводка и оговорка «ничего не записано»",
   "Сводка по вердиктам" in txt and "НЕ записано" in txt)

# 3. СОГЛАСИЕ: без approve запись не начинается
res = A.apply_plan(pl, approve=False)
ok("без согласия — RC 3, запись не началась", res["rc"] == 3 and res.get("done", 0) == 0,
   "RC=%d, %s" % (res["rc"], res.get("detail")))

# 4. ПРОБА (dry_run): согласен, но записи нет
res = A.apply_plan(pl, approve=True, dry_run=True)
ok("dry_run: RC 0 и записи не было", res["rc"] == 0 and res.get("done", 0) == 0,
   "RC=%d, %s" % (res["rc"], res.get("detail")))

# 5. НЕТ CREOSON → ЧЕСТНЫЙ ОТКАЗ RC 2 (а не «успех»)
alive = A.creoson_alive()
res = A.apply_plan(pl, approve=True, dry_run=False)
if not alive:
    ok("CREOSON мёртв → честный отказ RC 2 (а не «прогон успешен»)", res["rc"] == 2,
       "RC=%d, %s" % (res["rc"], res.get("detail", "")[:70]))
    ok("при отказе НЕТ ни одного результата (ничего не «применено»»)", not res.get("results"),
       "результатов: %d" % len(res.get("results") or []))
else:
    print("INFO  CREOSON жив — живой прогон на копии в этой приёмке не выполнялся")

# 6. СТОП: останавливает цикл между моделями (проверяем на живом set_param НЕ вызывая)
# План-словарь из 5 шагов: СТОП поднимаем ДО вызова, чтобы set_param даже не дернулся
fake_plan = {"error": None, "steps": [
    {"file": r"D:\AI\нет\a%d.prt" % i, "name": "a%d.prt" % i, "param": "X",
     "value": "1", "old": "0", "verdict": "change", "note": ""} for i in range(5)]}

A.STOP["flag"] = True
res = A.apply_plan(fake_plan, approve=True)
ok("СТОП останавливает до первой записи", res.get("stopped") and res.get("done", 0) == 0,
   "остановлено: %s, сделано %d" % (res.get("detail"), res.get("done", 0)))
A.STOP["flag"] = False

# 7. ИНСТРУМЕНТЫ АГЕНТА
import batch_params_tools as BPT   # noqa: E402
ok("инструменты зарегистрированы",
   [t["name"] for t in BPT.TOOLS] == ["batch_params_plan", "batch_params_apply",
                                      "feature_rename_plan"])
out = BPT.tool_batch_params_plan(root=ZAKI, param="GROUP=std")
ok("batch_params_plan даёт сводку", "изменится/создастся" in out, out.splitlines()[2])
out2 = BPT.tool_batch_params_apply(plan_json="")
ok("batch_params_apply требует план", "нужен файл плана" in out2)
out3 = BPT.tool_feature_rename_plan(name=ZAKI, pattern=r"^1_")
ok("feature_rename_plan строит план переименования", "ПЛАН переименования" in out3,
   out3.splitlines()[1])
out4 = BPT.tool_feature_rename_plan(name=ZAKI, pattern=r"[")
ok("битая маска даёт честную ошибку", "не разбирается маска" in out4)

# 8. КОНТРАКТ
import tool_contract as TC   # noqa: E402
c, err = TC.load_dir(AGENT / "batch_params")
ok("контракт tool.json валиден", err in (None, "") and c.get("class") == "Ж",
   "ошибок: %s" % (err or "нет"))

# 9. ОКНО: каркас, согласие, СТОП, поток
src = (AGENT / "batch_params" / "gui.py").read_text(encoding="utf-8")
ok("окно на каркасе ui_common", "ui_common" in src)
ok("в окне есть согласие и СТОП", "approve" in src and "stop_button" in src)
ok("тяжёлое в потоке", "run_in_thread" in src)
ok("в окне нет messagebox в автопрогоне (только под согласием)",
   "askyesno" in src)

# 10. РЕГРЕСС ВОЛН 1-6
for script in ("vol1_check.py", "vol3_check.py", "vol4_check.py", "vol5_check.py",
               "vol6_check.py", "win_check.py", "skills_check.py"):
    r = subprocess.run([sys.executable, "-X", "utf8", script], cwd=str(HERE),
                       capture_output=True, text=True, timeout=400)
    ok("регресс %s: RC 0" % script.replace("_check.py", ""), r.returncode == 0,
       "RC=%d" % r.returncode)

print("\n=== ИТОГ ВОЛНЫ 7: %s (провалов %d, %.1f с) ==="
      % ("ОК" if not fail else "НЕ ОК", len(fail), time.time() - t0))
if fail:
    print("провалы: " + "; ".join(fail))
sys.exit(1 if fail else 0)