# -*- coding: utf-8 -*-
"""ПРИЁМКА ВОЛНЫ 6 - аудит чертежа (drawing_audit, этап 4 плана).
Запуск: cmd /c "cd /d D:\\AI\\tools\\agent && python -X utf8 dev\\vol6_check.py"

Проверяет и волну 6, и регресс волн 1-5 (старые проверки должны работать по-своему).
"""
import io
import subprocess
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
AGENT = HERE.parent
sys.path.insert(0, str(AGENT))
sys.path.insert(0, str(AGENT / "drawing_audit"))

fail = []
t_start = time.time()


def ok(name, cond, detail=""):
    d = detail if isinstance(detail, str) else str(detail)
    print(("OK   " if cond else "FAIL ") + name + ((" | " + d) if d else ""))
    if not cond:
        fail.append(name)


import drawing_audit as DA   # noqa: E402

ETALON = DA.ETALON
ZAKL = str(ETALON.parent)

# 1. ДВИЖОК: эталонный чертёж разбирается и вердикты честные
ok("эталонный чертёж есть на диске", Path(ETALON).exists(), str(ETALON))
st = DA.load_settings()
rows = DA.check_file(ETALON, st)
ids = {r["id"] for r in rows}
ok("все 6 проверок отработали на эталоне", len(ids) == 6,
   "проверки: %s" % ", ".join(sorted(ids)))
sheet = next(r for r in rows if r["id"] == "sheet_size")
# ЛИСТ ЭТАЛОНА: 842x595 ПУНКТОВ = 297x210 мм = A4 АЛЬБОМНАЯ (не A3: A3 = 420x297 мм).
# Первая версия приёмки ждала A3 по ошибке комментария — движок прав, комментарий врёт.
ok("формат листа определён (эталон A4 альбом)", sheet["verdict"] == "ok" and "A4" in sheet["note"],
   sheet["note"])
txt = next(r for r in rows if r["id"] == "text_readable")
ok("текст эталона читается", txt["verdict"] == "ok", txt["note"])
gfx = next(r for r in rows if r["id"] == "graphics")
ok("эталон не объявлен пустым (нет ложных FAIL)", gfx["verdict"] == "ok", gfx["note"])
hatch = next(r for r in rows if r["id"] == "hatch")
ok("графика (штриховка) на эталоне найдена", hatch["verdict"] == "ok", hatch["note"])

# 2. ЛОЖНЫХ СРАБАТЫВАНИЙ НЕТ на боевой папке
res = DA.scan([Path(ZAKL)], st)
ok("боевая папка: чертежи найдены", res["checked"] >= 5,
   "чертежей: %d" % res["checked"])
ok("боевая папка: ошибок нет (титульные листы не считаются пустыми)", res["errors"] == 0,
   "ошибок: %d, предупреждений: %d" % (res["errors"], res["warns"]))
unread = [r for r in res["rows"] if r["id"] == "text_readable" and r["verdict"] == "warn"]
unread_names = {Path(r["path"]).name for r in unread}
ok("нечитаемый текст даёт warn, а не «нет плашек»",
   unread_names and all(
       r["verdict"] == "warn" for r in res["rows"]
       if r["id"] == "notes_present" and Path(r["path"]).name in unread_names),
   "нечитаемых файлов: %d (%s)" % (len(unread), ", ".join(sorted(unread_names))))

# 3. ЧЕК-ЛИСТ ПРАВИТСЯ ФАЙЛОМ, БЕЗ ПРАВКИ КОДА
alt = dict(st)
alt["notes"] = "ЗАВЕДОМО-НЕТ-ТАКОЙ-ПЛАШКИ"
res2 = DA.check_file(ETALON, alt)
n2 = next(r for r in res2 if r["id"] == "notes_present")
ok("чек-лист меняется настройкой без кода", n2["verdict"] == "warn"
   and "ЗАВЕДОМО" in n2["note"], n2["note"])
res3 = DA.check_file(ETALON, st)
ok("исходный чек-лист не задет (проверка независима)",
   next(r for r in res3 if r["id"] == "notes_present")["note"] != n2["note"])

# 4. НАСТРОЙКИ ПЕРЕЖИВАЮТ ЗАПУСК (файл, не только в памяти)
tmp_st = dict(st)
tmp_st["notes"] = "ПРОБА-ПЛАШКА"
p = DA.save_settings(tmp_st)
try:
    back = DA.load_settings()
    ok("настройки сохранены в файл и прочитаны обратно",
       back.get("notes") == "ПРОБА-ПЛАШКА", p)
finally:
    DA.save_settings(st)          # возвращаем боевой чек-лист
ok("боевой чек-лист восстановлен", DA.load_settings().get("notes") == st.get("notes"))

# 5. ОТЧЁТ И CSV
rp, cp = DA.write_report(res, 0.1)
ok("отчёт записан", Path(rp).exists(), rp)
ok("CSV записан", Path(cp).exists(), cp)
txt_r = Path(rp).read_text(encoding="utf-8")
ok("в отчёте есть сводка и замечания",
   "Сводка по чертежам" in txt_r and "Замечания" in txt_r)
# 6. CLI: RC 0/1/2 по контракту
r = subprocess.run([sys.executable, "-X", "utf8", "drawing_audit.py", ZAKL],
                   cwd=str(AGENT / "drawing_audit"), capture_output=True, text=True,
                   timeout=120)
ok("CLI отрабатывает (RC 0 или 1)", r.returncode in (0, 1), "RC=%d" % r.returncode)
r = subprocess.run([sys.executable, "-X", "utf8", "drawing_audit.py", r"D:\AI\нет-такой"],
                   cwd=str(AGENT / "drawing_audit"), capture_output=True, text=True,
                   timeout=60)
ok("CLI даёт RC 2, когда нечего проверять", r.returncode == 2, "RC=%d" % r.returncode)
r = subprocess.run("drawing_audit.bat", cwd=str(AGENT / "drawing_audit"),
                   capture_output=True, text=True, shell=True, timeout=180)
ok("bat запускается", r.returncode in (0, 1), "RC=%d" % r.returncode)

# 7. ПРЕВЬЮ
try:
    pv = DA.preview(ETALON, page=1, dpi=80)
    ok("превью строится", Path(pv).exists(), pv)
except Exception as e:
    ok("превью строится", False, str(e))

# 8. КОНТРАКТ И ИНСТРУМЕНТЫ АГЕНТА
import tool_contract as TC   # noqa: E402
# Контракт лежит в папке ПРОГРАММЫ (drawing_audit\tool.json), а не в папке с чертежами.
c, err = TC.load_dir(AGENT / "drawing_audit")
ok("контракт tool.json валиден", err in (None, "") and c.get("id") == "drawing_audit",
   "ошибок: %s" % (err or "нет"))
import drawing_audit_tools as DAT   # noqa: E402
ok("инструменты агента зарегистрированы",
   [t["name"] for t in DAT.TOOLS] == ["drawing_audit", "drawing_report"])
out = DAT.tool_drawing_audit(folder=ZAKL)
ok("инструмент drawing_audit даёт сводку", "ЧЕРТЕЖИ:" in out, out.splitlines()[0])
ok("фильтр only в инструменте работает",
   "ЧЕРТЕЖИ:" in DAT.tool_drawing_audit(folder=ZAKL, only="sheet_size"))

# 9. ЕДИНЫЙ ПРОГОН: новые проверки в каркасе
import checks as CH   # noqa: E402
ids = [c["id"] for c in CH.CHECKS]
ok("проверки drawing_notes и hatch_audit в едином прогоне",
   "drawing_notes" in ids and "hatch_audit" in ids, "всего проверок: %d" % len(ids))
r3 = CH.checks_run(scope="drawings", as_json=True)
ok("прогон по области drawings работает", r3["checks"] == 2,
   "проверок: %d, объектов: %d" % (r3["checks"], r3["items"]))

# 10. ОКНО: каркас, настройки, поток
src = (AGENT / "drawing_audit" / "gui.py").read_text(encoding="utf-8")
ok("окно на каркасе ui_common", "ui_common" in src)
ok("окно читает настройки из файла", "drawing_audit_settings.json" in src)
ok("тяжёлое в потоке", "run_in_thread" in src)

# 11. РЕГРЕСС ВОЛН 1-5: старые проверки работают по-своему
for script, name in (("vol1_check.py", "волна 1"), ("vol3_check.py", "волна 3"),
                     ("vol4_check.py", "волна 4"), ("vol5_check.py", "волна 5")):
    r = subprocess.run([sys.executable, "-X", "utf8", script], cwd=str(HERE),
                       capture_output=True, text=True, timeout=300)
    ok("регресс %s: RC 0" % name, r.returncode == 0, "RC=%d" % r.returncode)
r = subprocess.run([sys.executable, "-X", "utf8", "hol_check.py"],
                   cwd=str(AGENT / "hol_check"), capture_output=True, text=True,
                   timeout=180)
ok("старый hol_check работает по-своему", r.returncode in (0, 1), "RC=%d" % r.returncode)

print("\n=== ИТОГ ВОЛНЫ 6: %s (провалов %d, %.1f с) ==="
      % ("ОК" if not fail else "НЕ ОК", len(fail), time.time() - t_start))
if fail:
    print("провалы: " + "; ".join(fail))
sys.exit(1 if fail else 0)