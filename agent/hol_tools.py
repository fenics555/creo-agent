# -*- coding: utf-8 -*-
"""hol_tools.py — инструменты агента по таблицам отверстий (волна 3, блок *tools).

`hol_check` подключается автоматически (файл *_tools.py в папке агента) и даёт
агенту ту же проверку, что и окно, из того же движка — одна база, один код.
"""
import sys
from pathlib import Path

AGENT = Path(__file__).resolve().parent
sys.path.insert(0, str(AGENT / "hol_check"))


def tool_hol_check(folder="", as_json=False, **kw):
    """Проверить таблицы отверстий .hol (класс Р, только чтение).

    folder — папка с .hol; пусто = боевая папка и СТАРОЕ.
    Ловит разорванные имена колонок в шапке THREAD_DATA — причину ошибки
    `err_holechart`, из-за которой Creo не читал диаграммы (18.09.2026)."""
    try:
        import hol_check as eng
    except Exception as e:
        return "движок hol_check недоступен: %s" % e
    dirs = [folder] if folder else None
    res = eng.scan(dirs)
    if not res["files"]:
        return "нечего проверять: ни одного .hol в %s" % (folder or "боевые папки")
    if as_json:
        return res
    lines = ["ТАБЛИЦЫ ОТВЕРСТИЙ: файлов %d, ошибок %d, предупреждений %d"
             % (res["checked"], res["errors"], res["warns"])]
    for r in res["rows"]:
        if r["verdict"] != "ok":
            lines.append("  %-4s %-22s %-14s %s"
                         % (eng.ICON[r["verdict"]], Path(r["path"]).name, r["id"], r["note"]))
    lines.append("ВЕРДИКТ: %s" % ("есть ошибки — Creo может не прочитать диаграммы"
                                  if res["errors"] else "всё читаемо"))
    return "\n".join(lines)


def tool_hol_report(tail=20, **kw):
    """Последние отчёты проверки таблиц отверстий (папка отчётов)."""
    try:
        import hol_check as eng
    except Exception as e:
        return "движок hol_check недоступен: %s" % e
    rp = sorted(eng.REPORT_DIR.glob("REPORT_hol_check_*.md"))[-int(tail or 20):]
    return "\n".join("%s" % p for p in rp) or ("отчётов пока нет: %s" % eng.REPORT_DIR)


TOOLS = [
    {"name": "hol_check", "desc": "Проверить таблицы отверстий .hol: разорванные имена колонок, шапка, разделители (только чтение)",
     "params": {"folder": "папка с .hol или пусто", "as_json": "для витрины"},
     "fn": tool_hol_check, "kind": "check", "group": "Creo", "source": "hol_tools"},
    {"name": "hol_report", "desc": "Последние отчёты проверки таблиц отверстий",
     "params": {"tail": "сколько отчётов"}, "fn": tool_hol_report,
     "kind": "report", "group": "Creo", "source": "hol_tools"},
]