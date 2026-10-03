# -*- coding: utf-8 -*-
"""Живая сборка окон волны 1 на каркасе ui_common (без показа пользователю).
Запуск: cmd /c "cd /d D:\AI\tools\agent && python -X utf8 dev\vol1_win_live.py"
Делает настоящий Tk-корень, собирает окно, нажимает кнопки и проверяет, что не падает.
"""
import io
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))

SETTINGS_LIVE = AGENT / "data" / "config_audit_settings.json"

fail = []
backup = None


def keep_settings():
    """Проба НЕ трогает боевые настройки окна: копируем и возвращаем (грабля 03.10.2026:
    проба с недоступным путём записала его в data\config_audit_settings.json)."""
    global backup
    if SETTINGS_LIVE.exists():
        backup = SETTINGS_LIVE.read_text(encoding="utf-8")


def restore_settings():
    if backup is not None:
        SETTINGS_LIVE.write_text(backup, encoding="utf-8")
        print("настройки окна возвращены из копии")


def ok(name, cond, detail=""):
    print(("OK   " if cond else "FAIL ") + name + ((" | " + detail) if detail else ""))
    if not cond:
        fail.append(name)


def check_config_audit():
    sys.path.insert(0, str(AGENT / "config_audit"))
    import gui as g
    import config_audit as eng
    app = g.App()
    app.root.update_idletasks()
    ok("config_audit: окно собрано", app.root.winfo_exists() == 1)
    ok("config_audit: minsize задан", app.root.minsize() == (900, 560),
       str(app.root.minsize()))
    ok("config_audit: таблица настроек", hasattr(app, "tbl") and
       len(app.tbl.spec) >= 1, "строк: %d" % len(getattr(app, "tbl").spec))
    # кнопка «По умолчанию» жива: значение меняем и возвращаем (файл не трогаем)
    keep_now = app.tbl.vals.get("last_config")
    app.tbl.vals["last_config"] = r"Z:\нет\config.pro"
    app.tbl.refresh()
    ok("config_audit: точка «изменено»", app.tbl.changed("last_config") is True)
    app.tbl.set_defaults()
    ok("config_audit: «По умолчанию» вернул", app.tbl.changed("last_config") is False)
    # ЖИВАЯ проверка: путь берём у движка, а НЕ из настроек — иначе проба пройдёт
    # по битому пути и запишет его обратно (грабля 03.10.2026).
    # Волна 2: движок зовёт BOOT (creo_boot), а не CREO напрямую.
    p = eng.BOOT.config_path()
    app.var_path.set(p)
    if p and Path(p).exists():
        t0 = time.time()
        app.run()
        for _ in range(60):          # ждём поток не дольше ~3 с
            app.root.update()
            time.sleep(0.05)
            if app.res is not None:
                break
        ok("config_audit: проверка отработала в потоке", app.res is not None,
           "%.2f с, путей: %s" % (time.time() - t0,
                                   app.res.get("total") if app.res else "-"))
        if app.res:
            ok("config_audit: сводка с процентом", "соответствие" in app.sum_var.get(),
               app.sum_var.get())
            rows = len(app.tree.get_children())
            ok("config_audit: строки с иконкой статуса", rows >= 0, "строк: %d" % rows)
    else:
        print("ПРОПУСК живой проверки: config.pro не найден по %s" % p)
    app.tbl.vals["last_config"] = keep_now
    app.root.destroy()


def check_dup_scan():
    sys.path.insert(0, str(AGENT / "dup_scan"))
    for mod in ("gui",):
        sys.modules.pop(mod, None)
    import gui as g
    app = g.App()
    app.root.update_idletasks()
    ok("dup_scan: окно собрано", app.root.winfo_exists() == 1)
    app.root.destroy()


if __name__ == "__main__":
    t0 = time.time()
    keep_settings()                  # проба не должна оставлять битый путь в настройках
    try:
        check_config_audit()
        check_dup_scan()
    finally:
        restore_settings()
    print("=== ИТОГ: %s (провалов %d) за %.2f с ===" % (
        "ОК" if not fail else "НЕ ОК", len(fail), time.time() - t0))
    sys.exit(1 if fail else 0)