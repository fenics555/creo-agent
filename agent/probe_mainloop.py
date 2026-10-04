# -*- coding: utf-8 -*-
r"""probe_mainloop - ПРОБА: живёт ли mainloop окна (04.10.2026).

WHY: окно строится (probe_app_build: ИТОГ ОК), но процесс не держится. Разделяем
две причины: краш в mainloop ИЛИ у фоновой сессии нет интерактивного десктопа.
Здесь mainloop крутится 3 секунды и сам закрывается, попутно ПИШЕТ В ФАЙЛ —
это доказывает, что цикл событий реально крутится.
"""
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parent / "postregen_clean"
sys.path.insert(0, str(TOOL))
sys.path.insert(0, str(TOOL.parent))
OUT = TOOL / "probe_mainloop_out.txt"
TICKS = []


def main():
    import traceback
    import gui as G
    import ui_common as U
    r = U.make_root("ПРОБА MAINLOOP", "900x600", minsize=(700, 500))
    app = G.App(r)

    def tick(i=0):
        TICKS.append(i)
        # доказываем, что события идут: пишем в журнал окна
        app.log("тик %d" % i)
        if i < 5:
            r.after(400, tick, i + 1)
        else:
            r.after(300, finish)

    def finish():
        OUT.write_text("ТИКИ ГЛАВНОГО ЦИКЛА: %s\nИТОГ: mainloop жив\n" % TICKS,
                       encoding="utf-8")
        r.destroy()

    try:
        r.after(300, tick, 0)
        r.mainloop()
        return 0
    except Exception as e:
        OUT.write_text("ИТОГ: ОШИБКА %s\n%s\nТИКИ: %s"
                       % (e, traceback.format_exc(), TICKS), encoding="utf-8")
        return 2


if __name__ == "__main__":
    sys.exit(main())