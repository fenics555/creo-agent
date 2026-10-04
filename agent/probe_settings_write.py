# -*- coding: utf-8 -*-
r"""probe_settings_write - ПРОБА: окно реально пишет настройки (аудит 04.10.2026).

WHY: в отчёте стояло «файл настроек создаётся кнопкой Применить, но я не
нажимал её». Проверяем живым вызовом того же пути: build() -> save_settings.
Файл не должен существовать ДО пробы и должен появиться ПОСЛЕ.
"""
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parent / "postregen_clean"
sys.path.insert(0, str(TOOL))
sys.path.insert(0, str(TOOL.parent))
OUT = TOOL / "probe_settings_write_out.txt"


def main():
    import gui as G
    import ui_common as U
    lines = []
    p = U.settings_path(G.SETTINGS)
    lines.append("путь настроек: %s" % p)
    lines.append("файл существует ДО пробы: %s" % p.exists())

    root = U.make_root("ПРОБА НАСТРОЕК", "1000x700", minsize=(900, 600))
    app = G.App(root)
    app.log("проба")
    # Меняем значение ОДНОЙ настройки и жмём «Применить» — тот же путь, что
    # нажимает человек.
    app.tbl.vals["limit"] = "42"
    app.tbl.apply()
    root.update()
    root.destroy()

    lines.append("файл существует ПОСЛЕ пробы: %s" % p.exists())
    if p.exists():
        lines.append("содержимое: %s" % p.read_text(encoding="utf-8")[:400])
        # ВОЗВРАЩАЕМ значение пробы, чтобы не оставлять мусор в настройках.
        import json
        d = json.loads(p.read_text(encoding="utf-8"))
        d["limit"] = "100"
        p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        lines.append("значение limit возвращено: %s" % d["limit"])
    OUT.write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())