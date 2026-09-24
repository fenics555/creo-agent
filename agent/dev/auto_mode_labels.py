# -*- coding: utf-8 -*-
r"""Понятные подписи про авторежим: галка НЕ сбрасывает значения (они хранятся отдельно)."""
import re, shutil, traceback
from pathlib import Path

AG = Path(r"D:\AI\tools\agent")
REP = Path(r"D:\AI\log\reports\auto_mode_labels.txt")
rep = []
try:
    p = AG / "settings.py"
    shutil.copy2(p, AG / "data" / "backup" / "pre_auto_labels_settings.py")
    t = p.read_text(encoding="utf-8")
    subs = [
        (r'\("Главное", "creativity",[^\n]*\),',
         '("Главное", "creativity", "Креатив 0-100 (когда авторежим ВЫКЛ)", "int", 40, '
         '"0-34 строго, 35-66 нейтрально, 67-100 свободно. Значение хранится отдельно: переключение авторежима его НЕ сбрасывает.", True),'),
        (r'\("Главное", "auto_temperature",[^\n]*\),',
         '("Главное", "auto_temperature", "Температура при АВТОРЕЖИМЕ 0-100", "int", 10, '
         '"10 = 0.10 — инженерная строгость. Хранится отдельно от креатива.", True),'),
        (r'\("Главное", "auto_mode",[^\n]*\),',
         '("Главное", "auto_mode", "Авторежим", "bool", True, '
         '"Вкл: берётся «Температура при АВТОРЕЖИМЕ». Выкл: берётся «Креатив». Твои значения не сбрасываются.", True),'),
    ]
    for pat, new in subs:
        rr = re.compile(pat)
        t2, n = rr.subn(new, t, count=1)
        key = re.search(r'"([a-z_]+)"', new).group(1)
        rep.append("%s: заменено %d" % (key, n))
        t = t2
    p.write_text(t, encoding="utf-8", newline="\n")
except Exception:
    rep.append("ОШИБКА:\n" + traceback.format_exc())
REP.write_text("\n".join(rep), encoding="utf-8")
print("ok")
