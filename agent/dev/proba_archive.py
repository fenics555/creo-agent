# -*- coding: utf-8 -*-
r"""АРХИВ ПРОБ D:\AI\PROBA (24.09.2026): двигаем ТОЛЬКО то, на что в доме нет ссылок.
Заметки и скрипты, упомянутые в README/скиллах, остаются на месте (канон: чужое не трогаем).
Архив: D:\AI\repo\_proba_2026-09\ + README с объяснением."""
import re, shutil, traceback
from pathlib import Path

PROBA = Path(r"D:\AI\PROBA")
ARCH = Path(r"D:\AI\repo\_proba_2026-09")
LOOK = [Path(r"D:\AI\tools"), Path(r"D:\AI\repo")]
REPORT = Path(r"D:\AI\log\reports\proba_archive_2026-09-24.txt")

rep = []


def referenced(name):
    """Есть ли ссылка на файл по имени в коде/доках дома (кроме самого PROBA и _legacy)."""
    for root in LOOK:
        for p in root.rglob("*"):
            if p.is_dir() or p.suffix.lower() not in (".py", ".bat", ".md", ".json", ".html", ".js"):
                continue
            if "_legacy" in str(p) or "backup" in str(p) or "__pycache__" in str(p):
                continue
            try:
                t = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if name in t:
                return str(p.relative_to(root))
    return None


try:
    ARCH.mkdir(parents=True, exist_ok=True)
    moved, kept = [], []
    for f in sorted(PROBA.glob("*")):
        if f.is_dir():
            continue
        nm = f.name
        if f.suffix.lower() in (".md",):          # заметки/доки — не трогаем
            kept.append((nm, "заметка"))
            continue
        if nm in ("nav_gui_test.py", "make_lst.py", "smartcopy.py", "CREO-START.bat"):
            kept.append((nm, "оставлен как рабочий прототип/обвязка"))
            continue
        if f.suffix.lower() not in (".py", ".bat", ".json", ".vscdb"):
            kept.append((nm, "не скрипт/не проба"))
            continue
        ref = referenced(nm)
        if ref:
            kept.append((nm, "упомянут в " + ref))
            continue
        shutil.move(str(f), str(ARCH / nm))
        moved.append(nm)
    # пояснение к архиву
    readme = ARCH / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Архив проб (из D:\\AI\\PROBA, 24.09.2026)\n\n"
            "Сюда перенесены скрипты-пробы прошлых сессий, **на которые в доме нет ссылок**\n"
            "(проверено поиском по `D:\\AI\\tools` и `D:\\AI\\repo`). Не удалены по канону дома.\n"
            "Заметки (`AGENT_NOTES.md`, `POLYGON_NOTES.md`, `jlink_direct_probe_notes.md`, `SESSION_STATE_2209.md`)\n"
            "остались в `D:\\AI\\PROBA` — на них ссылаются скиллы и карта агента.\n",
            encoding="utf-8", newline="\n")
    rep.append("перенесено в архив: %d файлов -> %s" % (len(moved), ARCH))
    rep.append("оставлено в PROBA: %d файлов" % len(kept))
    rep.append("")
    rep.append("ОСТАВЛЕНО (с причиной):")
    for nm, why in kept:
        rep.append("  %-32s %s" % (nm, why))
except Exception:
    rep.append("ОШИБКА:\n" + traceback.format_exc())
REPORT.write_text("\n".join(rep), encoding="utf-8")
print("ok")
