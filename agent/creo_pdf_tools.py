# -*- coding: utf-8 -*-
r"""АГЕНТ — БЛОК CREO PDF (creo_pdf_tools.py)
Рутина дома: рядом с чертежом <имя>.drw[.N] обязан лежать <имя>.pdf и быть не старше чертежа.
Исполнитель: D:\AI\tools\agent\creo_pdf\creo_pdf.bat — прямой JLINK (без CREOSON).
PDF делается домашним конфигом Creo (форматки ФОРМАТЫ, MY_ESKD.dtl, table.pnt).
"""
import subprocess
from pathlib import Path

BAT = r"D:\AI\tools\agent\creo_pdf\creo_pdf.bat"
LAST = Path(r"D:\AI\tools\agent\data\tmp\creo_pdf_last.txt")


def _run(args, timeout):
    LAST.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.run(["cmd", "/c", "call", BAT] + list(args),
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=timeout, cwd=str(Path(BAT).parent))
    out = ((p.stdout or "") + (p.stderr or "")).strip()
    try:
        LAST.write_text(out, encoding="utf-8")
    except Exception:
        pass
    return out


def tool_pdf_scan(folder="", **kw):
    """Отчёт по папке: где рядом с чертежом нет PDF или PDF старше чертежа. Creo НЕ нужен."""
    if not folder:
        return 'нужна папка: creo_pdf_scan {"folder": "Z:\\\\PTC\\\\Work\\\\..."}'
    try:
        out = _run(["scan", folder], 1800)
    except subprocess.TimeoutExpired:
        return "скан не уложился в 30 мин (папка слишком большая — дай подпапку)"
    lines = [l for l in out.splitlines() if l.strip()]
    tail = [l for l in lines if l.startswith("чертежей:")]
    body = [l for l in lines[:40] if l not in tail]
    return "\n".join(body) + ("\n…" if len(lines) > 40 else "") + ("\n" + tail[0] if tail else "")


def tool_pdf_export(folder="", limit="20", **kw):
    """Создать недостающие/устаревшие PDF в папке. Нужен запущенный Creo."""
    if not folder:
        return "нужна папка"
    try:
        lim = int(str(limit) or 20)
    except Exception:
        lim = 20
    try:
        out = _run(["export", folder, str(lim)], 7200)
    except subprocess.TimeoutExpired:
        return "экспорт не уложился в 2 часа — уменьшай лимит и дели папку"
    lines = [l for l in out.splitlines() if l.strip()]
    return "\n".join(lines[-25:])


TOOLS = [
    {"name": "creo_pdf_scan",
     "desc": "PDF-рутина: отчёт по папке — где нет PDF рядом с чертежом или PDF старше чертежа",
     "params": {"folder": "папка"}, "approval": False, "fn": tool_pdf_scan},
    {"name": "creo_pdf_export",
     "desc": "PDF-рутина: создать недостающие/устаревшие PDF в папке (Creo должен быть запущен)",
     "params": {"folder": "папка", "limit": "лимит"}, "approval": True, "fn": tool_pdf_export},
]