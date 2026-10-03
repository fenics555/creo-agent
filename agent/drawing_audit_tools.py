# -*- coding: utf-8 -*-
"""drawing_audit_tools.py - инструменты агента по аудиту чертежа (волна 6, блок *tools).

Подключается автоматически (файл *_tools.py в папке агента) и даёт агенту тот же
аудит, что и CLI, и окно, - из одного движка (одна база, один код, закон трёх рук).
"""
import sys
from pathlib import Path

AGENT = Path(__file__).resolve().parent
sys.path.insert(0, str(AGENT / "drawing_audit"))

CHECKS = ("sheet_size", "text_readable", "notes_present", "graphics",
          "hatch", "empty_page")


def tool_drawing_audit(folder="", only="", as_json=False, **kw):
    """Проверить PDF-чертежи: формат листа, читаемость текста, плашки по чек-листу,
    графика (штриховка), пустые страницы (класс Р, только чтение).

    folder — папка с PDF-чертежами; пусто = боевые 4 папки библиотеки.
    only  — что проверить, например `notes_present,hatch`; пусто = всё."""
    try:
        import drawing_audit as eng
    except Exception as e:
        return "движок drawing_audit недоступен: %s" % e
    st = eng.load_settings()
    dirs = [Path(folder)] if folder else [Path(d) for d in (st.get("folders")
                                                           or eng.DEFAULT_DIRS)]
    res = eng.scan(dirs, st)
    if only:
        want = {x.strip() for x in str(only).split(",") if x.strip()}
        res["rows"] = [r for r in res["rows"] if r["id"] in want]
        res["errors"] = sum(1 for r in res["rows"] if r["verdict"] == "error")
        res["warns"] = sum(1 for r in res["rows"] if r["verdict"] == "warn")
    if not res["files"]:
        return "нечего проверять: ни одного PDF-чертежа в %s" % (folder or "боевые папки")
    if as_json:
        return res
    lines = ["ЧЕРТЕЖИ: файлов %d, ошибок %d, предупреждений %d"
             % (res["checked"], res["errors"], res["warns"]),
             "чек-лист плашек: %s" % st.get("notes", "")]
    for r in res["rows"]:
        if r["verdict"] != "ok":
            lines.append("  %-4s %-26s %-14s %s"
                         % (eng.ICON[r["verdict"]], Path(r["path"]).name, r["id"], r["note"]))
    lines.append("ВЕРДИКТ: %s" % ("есть ошибки" if res["errors"]
                                  else "ошибок нет (%d предупреждений)" % res["warns"]))
    return "\n".join(lines)


def tool_drawing_report(tail=20, **kw):
    """Последние отчёты аудита чертежа."""
    try:
        import drawing_audit as eng
    except Exception as e:
        return "движок drawing_audit недоступен: %s" % e
    rp = sorted(eng.REPORT_DIR.glob("REPORT_drawing_audit_*.md"))[-int(tail or 20):]
    return "\n".join("%s" % p for p in rp) or ("отчётов пока нет: %s" % eng.REPORT_DIR)


TOOLS = [
    {"name": "drawing_audit",
     "desc": "Проверить PDF-чертежи без Creo: формат листа, читаемость текста, "
             "обязательные плашки по чек-листу, графика/штриховка, пустые листы",
     "params": {"folder": "папка с PDF или пусто", "only": "что проверить через запятую",
                "as_json": "для витрины"},
     "fn": tool_drawing_audit, "kind": "check", "group": "Creo",
     "source": "drawing_audit_tools"},
    {"name": "drawing_report", "desc": "Последние отчёты аудита чертежа",
     "params": {"tail": "сколько отчётов"}, "fn": tool_drawing_report,
     "kind": "report", "group": "Creo", "source": "drawing_audit_tools"},
]