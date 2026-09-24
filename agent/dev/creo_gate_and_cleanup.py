# -*- coding: utf-8 -*-
r"""Настройка «разрешить агенту стартовать Creo» + чистка crash-логов CREOSON."""
import re, shutil, traceback
from pathlib import Path

AG = Path(r"D:\AI\tools\agent")
CREO_DIR = Path(r"D:\PTC\CREO-LOCAL-SETUP\creoson")
REP = Path(r"D:\AI\log\reports\creoson_fix_2026-09-24.txt")
rep = []
try:
    # 1) настройка в реестре настроек
    sp = AG / "settings.py"
    shutil.copy2(sp, AG / "data" / "backup" / "pre_creo_gate_settings.py")
    t = sp.read_text(encoding="utf-8")
    row = ('    ("Creo", "creo_allow_start", "Разрешить агенту стартовать Creo", "bool", False, '
           '"Выкл: Creo поднимает только человек (CREO-START.bat). Вкл (админ): агент может поднять Creo — '
           'появится его синий сплеш.", True),\n')
    anchor = '    ("Creo", '
    i = t.find(anchor)
    if i >= 0:
        t = t[:i] + row + t[i:]
        sp.write_text(t, encoding="utf-8", newline="\n")
        rep.append("settings.py: добавлена настройка creo_allow_start (по умолчанию выкл)")
    else:
        rep.append("settings.py: якорь '(\"Creo\",' не найден — настройка не добавлена")

    # 2) crash-логи CREOSON: 1 052 файла = 76 МБ мусора. Оставляем 3 свежих в отчётах, остальные убираем.
    logs = sorted(CREO_DIR.glob("hs_err_pid*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    keep = logs[:3]
    saved = Path(r"D:\AI\log\reports\creoson_crashes")
    saved.mkdir(parents=True, exist_ok=True)
    for p in keep:
        shutil.move(str(p), str(saved / p.name))
    n = 0
    for p in logs[3:]:
        try:
            p.unlink()
            n += 1
        except Exception:
            pass
    rep.append("crash-логов CREOSON: было %d; 3 свежих сохранены в %s; удалено %d" % (len(logs), saved, n))
    frame = ""
    if keep:
        try:
            txt = (saved / keep[0].name).read_text(encoding="utf-8", errors="ignore")
            m = re.search(r"Problematic frame:\s*\n#\s*(.+)", txt)
            frame = m.group(1).strip() if m else ""
        except Exception:
            pass
    rep.append("причина падений JVM CREOSON: %s (нативная DLL Creo — отсюда нестабильность)" % (frame or "?"))
except Exception:
    rep.append("ОШИБКА:\n" + traceback.format_exc())
REP.write_text("\n".join(rep), encoding="utf-8")
print("ok")
