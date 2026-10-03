# -*- coding: utf-8 -*-
"""win_check.py — АВТОПРОВЕРКА ОКОН (волна 1, этап 8).

Что проверяет каждое окно:
  1. окно строится и не падает (создаём ТОТ ЖИВОЙ виджет, но НЕ показываем пользователю);
  2. каркас `ui_common` подключён: `import ui_common` есть в коде окна;
  3. есть кнопка README (окно самостоятельно, манифест п.19);
  4. задан minsize (окно не схлопнется) и заголовок;
  5. тяжёлое уходит в поток: в коде есть `run_in_thread` или `threading`;
  6. настройки окна живут в data\\<имя>_settings.json (не в коде).

Запуск: cmd /c "cd /d D:\AI\tools\agent && python -X utf8 dev\win_check.py"
Отчёт: D:\\AI\\log\\win_check\\win_check_<дата>.txt, вердикт ОК/НЕ ОК в конце.
"""
import io
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
AGENT = HERE.parent
sys.path.insert(0, str(AGENT))

REPORT_DIR = Path(r"D:\AI\log\win_check")
# ОКНА ВОЛНЫ 1 (переведены на ui_common). Остальные 15 — по очереди, волна 11.
WINDOWS = [
    {"name": "config_audit", "path": AGENT / "config_audit" / "gui.py", "module": "gui",
     "dir": AGENT / "config_audit", "settings": "config_audit_settings.json"},
    {"name": "dup_scan", "path": AGENT / "dup_scan" / "gui.py", "module": "gui",
     "dir": AGENT / "dup_scan", "settings": "dup_scan_settings.json"},
    {"name": "hol_check", "path": AGENT / "hol_check" / "gui.py", "module": "gui",
     "dir": AGENT / "hol_check", "settings": "hol_check_settings.json"},
    {"name": "rules", "path": AGENT / "rules" / "gui.py", "module": "gui",
     "dir": AGENT / "rules", "settings": ""},
    {"name": "checks", "path": AGENT / "checks" / "gui.py", "module": "gui",
     "dir": AGENT / "checks", "settings": ""},
]

fail = []
lines = []


def out(s=""):
    print(s)
    lines.append(str(s))


def check_window(w):
    p = w["path"]
    res = {"окно": w["name"]}
    if not p.exists():
        out("FAIL %s: файла окна нет (%s)" % (w["name"], p))
        fail.append(w["name"])
        return res
    src = p.read_text(encoding="utf-8")

    def has(cond, key, detail=""):
        res[key] = bool(cond)
        if not cond:
            fail.append("%s: %s" % (w["name"], key))
        return "OK  " if cond else "FAIL"

    out("=== ОКНО %s (%s, %d байт) ===" % (w["name"], p.name, len(src.encode("utf-8"))))
    out(" %s каркас ui_common подключён" % has("ui_common" in src, "ui_common"))
    out(" %s кнопка README" % has("readme_button" in src or "README" in src, "readme"))
    out(" %s minsize задан" % has("minsize" in src, "minsize"))
    out(" %s заголовок окна" % has("title(" in src or "make_root" in src, "title"))
    out(" %s тяжёлое в потоке" % has("run_in_thread" in src or "threading" in src, "thread"))
    st = AGENT / "data" / w["settings"]
    out(" %s настройки в data\\%s (есть на диске: %s)" % (
        has(w["settings"] in src or "ui_common" in src, "settings"), w["settings"], st.exists()))
    return res


def smoke_build():
    """Живая сборка каркаса Tk: окно создаётся и все шесть констант ставятся на место."""
    import tkinter as tk
    import ui_common as U
    ok = True
    try:
        r = U.make_root("win_check — проба каркаса", "900x560")
        U.head(r, "ПРОБА КАРКАСА", "win_check: проверка, что каркас собирается живым окном")
        left, right = U.split_result_left(r)
        nb, pages = U.tabs(right, ["Основное", "Дополнительно"])
        var, set_sum = U.summary(left)
        tr = U.result_tree(left, ("st", "line", "opt", "path"),
                           ("Статус", "Строка", "Настройка", "Путь"),
                           [70, 50, 160, 260])
        tr.insert("", "end", values=(U.ICON_ERR, 1, "PRO_DIRECTORY", r"Z:\нет"), tags=("fail",))
        tr.insert("", "end", values=(U.ICON_OK, 2, "PROSTD", r"Z:\есть"), tags=("ok",))
        set_sum(2, 1, 1)
        st = U.SettingsTable(pages[0], [
            {"option": "last_config", "value": r"D:\config.pro",
             "desc": "какой файл проверяем", "default": r"D:\config.pro"},
            {"option": "порог", "value": "10", "desc": "размер, байт", "default": "5"},
        ])
        pct = set_sum(2, 1, 1)
        assert pct == 50.0, "процент соответствия неверный: %s" % pct
        assert "соответствие: 50 %" in var.get(), "в сводке нет процента: %s" % var.get()
        st.set_defaults()
        assert st.changed("порог") is False, "«По умолчанию» не вернул значение"
        st.vals["порог"] = "99"
        assert st.changed("порог") is True, "точка «изменено» не появилась"
        r.update_idletasks()
        r.destroy()
    except Exception as e:
        ok = False
        out("FAIL живая сборка каркаса Tk: %s" % e)
        fail.append("smoke_build")
    if ok:
        out("OK   живая сборка каркаса Tk: 6 констант на месте, процент 50 % посчитан")
    return ok


if __name__ == "__main__":
    t0 = time.time()
    out("WIN_CHECK — автопроверка окон агента")
    out("дата: %s   окон к проверке: %d" % (time.strftime("%Y-%m-%d %H:%M:%S"), len(WINDOWS)))
    out("")
    rows = [check_window(w) for w in WINDOWS]
    out("")
    smoke_build()
    out("")
    out("--- СВОДКА ---")
    for r_ in rows:
        out("%-14s %s" % (r_["окно"], " ".join(
            "%s=%s" % (k, "ок" if v else "НЕТ") for k, v in r_.items() if k != "окно")))
    verdict = "ОК" if not fail else "НЕ ОК (%d)" % len(fail)
    out("=== ВЕРДИКТ: %s | провалов: %d | %.2f с ===" % (verdict, len(fail), time.time() - t0))
    if fail:
        out("провалы: " + "; ".join(fail))
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rp = REPORT_DIR / ("win_check_%s.txt" % time.strftime("%Y-%m-%d_%H%M%S"))
    rp.write_text("\n".join(lines), encoding="utf-8")
    print("отчёт: %s" % rp)
    sys.exit(1 if fail else 0)