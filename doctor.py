# -*- coding: utf-8 -*-
import re
from pathlib import Path
AG = Path(r"D:\AI\tools\agent")
import sys; sys.path.insert(0, str(AG)); sys.path.insert(0, str(AG.parent))
import core

# 1) правило по параметрам — в базу знаний
sk = core.REPO / "SKILL_parameters.md"
sk.write_text('''# ПАРАМЕТРЫ МОДЕЛЕЙ (источники правды)
1. ОБОЗНАЧЕНИЕ / НАИМЕНОВАНИЕ(+1/2) — внутренние шифры КБ. Источник правды для спецификаций, чертежей, индексов; по ним выводятся детали в спецах.
2. CATALOG_NUMBER / CATALOG_NAME(+1/2) — ВНЕШНИЕ ссылки на каталоги других производств/машин. НЕ совпадают с реальными шифрами; чужие шифры в наши каталоги не вставляются. Отдельные независимые параметры.
3. NAME_1/2, NAME_1_ENG — латинские дублёры для интеграций.
4. Аудит: уникальность — по ОБОЗНАЧЕНИЕ. CATALOG_* — ТОЛЬКО для кросс-аудита коллизий (две наши детали с одним каталожным; наш шифр = чужой каталожный), не как источник шифра.
5. Русские параметры не убиваем; ISO набиваем рядом только при появлении потребителя, через отношение (синхронно).
''', encoding="utf-8")
print("[+] SKILL_parameters.md: источники правды + аудит по ОБОЗНАЧЕНИЕ")

# 2) usage_tools: UNC-фолбэк для сетевых корней + диагностика
p = AG / "usage_tools.py"
s = p.read_text(encoding="utf-8")
ch = False
if "import subprocess" not in s:
    s = s.replace("import os, re, threading, time", "import os, re, threading, time, subprocess", 1); ch = True
if "_unc_roots" not in s:
    helper = '''
def _unc_roots():
    roots = core.read_roots()
    m = {}
    try:
        out = subprocess.run(["net", "use"], capture_output=True, text=True).stdout
        m = dict(re.findall(r"([A-Za-z]):\\s+(\\\\\\\\\\S+)", out))
    except Exception:
        pass
    res = []
    for r in roots:
        d = r[:2]
        if not os.path.exists(r) and d in m:
            r = m[d] + r[2:]
        res.append(r)
    return res
'''
    s = s.replace("def build_usage(", helper + "\ndef build_usage(", 1); ch = True
if "for root in core.read_roots():" in s:
    s = s.replace("for root in core.read_roots():", "for root in _unc_roots():", 1); ch = True
if 'STATE["roots_info"]' not in s:
    s = s.replace('STATE["total"] = len(tasks)',
                  'STATE["roots_info"] = "; ".join("%s:%s" % (r, "есть" if os.path.exists(r) else "НЕТ") for r in _unc_roots())\n    STATE["total"] = len(tasks)', 1)
    s = s.replace('return "индекс готов (%s): ссылок %d (имён в словаре %d, asm-файлов %d). Спрашивай models_where" % (STATE["finished"], STATE["links"], STATE["names"], STATE["total"])',
                  'return "индекс готов (%s): ссылок %d (имён %d, asm %d). Корни: %s. Спрашивай models_where" % (STATE["finished"], STATE["links"], STATE["names"], STATE["total"], STATE.get("roots_info", ""))', 1)
    ch = True
if ch:
    p.write_text(s, encoding="utf-8")
    print("[+] usage_tools: UNC-фолбэк + диагностика корней")
print("ГОТОВО: .\\AI_RESTART.bat, затем usage_build full=1 -> usage_state (увидишь, какие корни НЕТ)")