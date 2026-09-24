# -*- coding: utf-8 -*-
"""Правка описания num_ctx: 0 = как в модели (агент подставит её окно), иначе Ollama даёт 4096."""
import re, shutil, traceback
from pathlib import Path

AG = Path(r"D:\AI\tools\agent")
REP = Path(r"D:\AI\log\reports\ctx_desc_patch.txt")
rep = []
try:
    p = AG / "settings.py"
    shutil.copy2(p, AG / "data" / "backup" / "pre_ctx_desc_settings.py")
    t = p.read_text(encoding="utf-8")
    pat = re.compile(r'\("Главное", "num_ctx",[^\n]*\),')
    new = ('("Главное", "num_ctx", "Окно контекста (цифрой)", "int", 131072, '
           '"Впиши цифру. 0 = как в модели (агент сам подставит её окно; '
           'без этого Ollama по умолчанию даёт всего 4096!).", True),')
    t2, n = pat.subn(new, t, count=1)
    p.write_text(t2, encoding="utf-8", newline="\n")
    rep.append("num_ctx: заменено строк %d" % n)
    for line in t2.splitlines():
        if '"num_ctx"' in line:
            rep.append("  " + line.strip())
except Exception:
    rep.append("ОШИБКА:\n" + traceback.format_exc())
REP.write_text("\n".join(rep), encoding="utf-8")
print("ok")