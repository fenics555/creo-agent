# -*- coding: utf-8 -*-
r"""АГЕНТ — БЛОК CREO EXPORT (creo_export_tools.py)
Выгрузка модели из ЖИВОГО Creo в STEP/IGES/VRML/PDF/NEUTRAL/DXF3D/STL — прямой JLINK, без CREOSON.
Исполнитель: D:\AI\tools\agent\creo_export\creo_export.bat (пути берутся из настроек, Creo ищется сам).
Требуется ЗАПУЩЕННЫЙ Creo. Пишущий инструмент — всегда под щитом согласования (approval: True).
"""
import subprocess
from pathlib import Path

BAT = r"D:\AI\tools\agent\creo_export\creo_export.bat"
LAST = Path(r"D:\AI\tools\agent\data\tmp\creo_export_last.txt")
FORMATS = ["step", "iges", "vrml", "pdf", "neutral", "dxf3d", "stl"]


def _run(args, timeout):
    LAST.parent.mkdir(parents=True, exist_ok=True)
    # cmd /c call — единственная надёжная форма вызова bat с пробелами в путях
    # (находка 23.09.2026, закреплена в README инструмента).
    p = subprocess.run(["cmd", "/c", "call", BAT] + list(args),
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=timeout, cwd=str(Path(BAT).parent))
    out = ((p.stdout or "") + (p.stderr or "")).strip()
    try:
        LAST.write_text(out, encoding="utf-8")
    except Exception:
        pass
    return out, p.returncode


def tool_creo_export(fmt="step", model="", out="", **kw):
    """Выгрузить модель из живого Creo в заданный формат. Нужен запущенный Creo.
    model — имя как видит Creo (без версии .1) либо полный путь к файлу (предпочтительно)."""
    f = str(fmt or "").strip().lower()
    if f not in FORMATS:
        return "неизвестный формат %r. Доступны: %s" % (f, ", ".join(FORMATS))
    m = str(model or "").strip()
    if not m:
        return ('нужна модель: creo_export {"model": "D:\\\\path\\\\file.prt", "fmt": "step"}\n'
                'имя — как видит Creo, БЕЗ версии .1 (пишут: qr.prt, не qr.prt.1)')
    args = [f, m]
    if out:
        args.append(str(out).strip())
    try:
        text, code = _run(args, 1800)
    except subprocess.TimeoutExpired:
        return "выгрузка не уложилась в 30 мин"
    lines = [l for l in text.splitlines() if l.strip()
             and not l.startswith("WARNING") and "Restricted methods" not in l]
    tail = "\n".join(lines[-12:])
    return tail + ("\nкод возврата: %s" % code)


TOOLS = [
    {"name": "creo_export",
     "desc": "Выгрузка модели из ЖИВОГО Creo: step|iges|vrml|pdf|neutral|dxf3d|stl "
             "(pdf — только с ЧЕРТЕЖА; имя модели без версии .1 или полный путь)",
     "params": {"fmt": "формат", "model": "модель", "out": "папка вывода (пусто = out\\ рядом)"},
     "approval": True, "fn": tool_creo_export},
]
