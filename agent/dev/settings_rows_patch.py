# -*- coding: utf-8 -*-
r"""Правка строк настроек: окно цифрой, ответ без ограничения, понятные подписи."""
import re, shutil, traceback
from pathlib import Path

AG = Path(r"D:\AI\tools\agent")
OUT = Path(r"D:\AI\log\reports\settings_rows_patch.txt")
rep = []
try:
    p = AG / "settings.py"
    shutil.copy2(p, AG / "data" / "backup" / "pre_ctx_number_settings.py")
    t = p.read_text(encoding="utf-8")
    pat_ctx = re.compile(r'\("Главное", "num_ctx",[^\n]*\),')
    pat_np = re.compile(r'\("Главное", "num_predict",[^\n]*\),')
    new_ctx = ('("Главное", "num_ctx", "Окно контекста (цифрой)", "int", 131072, '
               '"Впиши цифру (сколько может модель — смотри «СОСТОЯНИЕ АГЕНТА»). '
               '0 = не задавать: Ollama возьмёт своё по умолчанию (часто всего 4096!).", True),')
    new_np = ('("Главное", "num_predict", "Длина ответа (токенов)", "int", 4096, '
              '"0 = БЕЗ ограничения (ответ не обрезать). Больше нуля — предел генерации.", True),')
    t2, n1 = pat_ctx.subn(new_ctx, t, count=1)
    t2, n2 = pat_np.subn(new_np, t2, count=1)
    p.write_text(t2, encoding="utf-8", newline="\n")
    rep.append("num_ctx: заменено строк %d" % n1)
    rep.append("num_predict: заменено строк %d" % n2)
    for k in ("num_ctx", "num_predict"):
        for line in t2.splitlines():
            if '"%s"' % k in line:
                rep.append("  " + line.strip())
except Exception:
    rep.append("ОШИБКА:\n" + traceback.format_exc())
OUT.write_text("\n".join(rep), encoding="utf-8")
print("ok")
