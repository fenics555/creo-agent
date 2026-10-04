# -*- coding: utf-8 -*-
r"""probe_app_build - ПРОБА: окно postregen_clean собирается целиком (04.10.2026).

WHY: запущенный gui.py исчезает без следа — надо проверить сам build(), а не
угадывать. Собираем окно, делаем update(), пишем маркер и закрываем. Никаких
записей в Creo: программа в этой пробе только ЧИТАЕТ настройки.
"""
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parent / "postregen_clean"
sys.path.insert(0, str(TOOL))
sys.path.insert(0, str(TOOL.parent))
OUT = TOOL / "probe_app_build_out.txt"
lines = []


def main():
    import traceback
    try:
        import gui as G
        import ui_common as U
        lines.append("импорт gui: ОК")
        root = U.make_root("ПРОБА ОКНА", "1200x740", minsize=(1020, 640))
        app = G.App(root)
        root.update()
        lines.append("App собран: ОК")
        lines.append("настроек в таблице: %d" % len(app.tbl.vals))
        lines.append("кнопок дерева: %d" % len(app.tree.get_children()))
        lines.append("журнал создан: %s" % (app._log_write is not None))
        lines.append("настройки из файла: %s" % U.load_settings(G.SETTINGS))
        root.destroy()
        lines.append("ИТОГ: ОК")
    except Exception as e:
        lines.append("ИТОГ: ОШИБКА %s\n%s" % (e, traceback.format_exc()))
    OUT.write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())