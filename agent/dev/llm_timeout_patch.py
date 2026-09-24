# -*- coding: utf-8 -*-
r"""Таймаут одного ответа модели (защита от зацикливания) + понятное сообщение при обрыве по времени."""
import re, shutil, traceback
from pathlib import Path

AG = Path(r"D:\AI\tools\agent")
REP = Path(r"D:\AI\log\reports\llm_timeout_patch.txt")
rep = []
try:
    p = AG / "loop.py"
    shutil.copy2(p, AG / "data" / "backup" / "pre_timeout_loop.py")
    t = p.read_text(encoding="utf-8")

    helper = ('def _llm_t():\n'
              '    """Таймаут ОДНОГО ответа модели, секунд.\n'
              '    Живой урок 24.09.2026: зациклившаяся модель молотила минутами (GPU занят, результата нет).\n'
              '    Теперь у каждого вызова к модели есть предел времени — дом честно скажет и не будет жечь впустую."""\n'
              '    try:\n'
              '        return max(30, int(settings.get("llm_timeout") or 240))\n'
              '    except Exception:\n'
              '        return 240\n\n\n')
    anchor = "def _native_think():"
    if anchor in t:
        t = t.replace(anchor, helper + anchor, 1)
        rep.append("loop.py: добавлен _llm_t() (таймаут ответа модели)")
    else:
        rep.append("loop.py: ЯКОРЬ _native_think не найден")

    n = t.count("t=600")
    t = t.replace("t=600", "t=_llm_t()")
    rep.append("loop.py: заменено вызовов t=600 -> t=_llm_t(): %d" % n)

    old_exc = '                return {"answer": _clean("ошибка модели: %s" % e), "think": "", "steps": step + 1, "log": steps_log}'
    new_exc = ('                _em = str(e)\n'
               '                if "timed out" in _em.lower() or "timeout" in _em.lower():\n'
               '                    _em = ("модель не уложилась в отведённое время (%d с) — похоже, зациклилась. "\n'
               '                           "Уменьши «Длина ответа (токенов)» или выбери модель попроще." % _llm_t())\n'
               '                return {"answer": _clean("ошибка модели: %s" % _em), "think": "", "steps": step + 1, "log": steps_log}')
    if old_exc in t:
        t = t.replace(old_exc, new_exc, 1)
        rep.append("loop.py: добавлено понятное сообщение при обрыве по времени")
    else:
        rep.append("loop.py: строка обработки ошибки модели не найдена (пропущено)")
    p.write_text(t, encoding="utf-8", newline="\n")

    # настройка в панели
    sp = AG / "settings.py"
    shutil.copy2(sp, AG / "data" / "backup" / "pre_timeout_settings.py")
    ts = sp.read_text(encoding="utf-8")
    row = ('    ("Разум", "llm_timeout", "Таймаут ответа модели, сек", "int", 240, '
           '"Предел времени на один ответ. Защита от зацикливания (GPU не жжём впустую).", True),\n')
    a2 = '    ("Разум", "think_lines_max"'
    if a2 in ts:
        ts = ts.replace(a2, row + a2, 1)
        sp.write_text(ts, encoding="utf-8", newline="\n")
        rep.append("settings.py: добавлен llm_timeout (240 с по умолчанию)")
    else:
        rep.append("settings.py: якорь think_lines_max не найден")
except Exception:
    rep.append("ОШИБКА:\n" + traceback.format_exc())
REP.write_text("\n".join(rep), encoding="utf-8")
print("ok")
