# -*- coding: utf-8 -*-
r"""readme_fix — обновить README инструментов после Волны 2.2 (настройки в папке).

Заменяет устаревшие пути data\<tool>_settings.json (и абс./agent\ варианты) на
<tool>\settings\settings.json. Каждая замена проверяется. Запуск: readme_fix.py
"""
import re
import sys
from pathlib import Path

AGENT = Path(r"D:\AI\tools\agent")
TOOLS = ["log_clean", "creo_comb", "excel", "navigator", "drawing_audit",
         "orphan_scan", "purge_versions", "config_audit"]


def main():
    fails, total = [], 0
    for tool in TOOLS:
        p = AGENT / tool / "README.md"
        if not p.exists():
            fails.append("%s: нет README" % tool)
            continue
        s = p.read_text(encoding="utf-8")
        pat = re.compile(r'(?:D:\\AI\\tools\\agent\\)?(?:agent\\)?data\\' + tool + r'_settings\.json')
        ns, n = pat.subn(lambda m: tool + '\\settings\\settings.json', s)
        if tool == "purge_versions":  # опечатка в README: purge_settings -> purge_versions
            ns, n2 = re.subn(r'data\\purge_settings\.json',
                             lambda m: 'purge_versions\\settings\\settings.json', ns)
            n += n2
        if n:
            p.write_text(ns, encoding="utf-8")
            total += n
            print("OK %-16s %d замен -> settings\\settings.json" % (tool, n))
        else:
            print("-- %-16s путей не найдено" % tool)
    print("--- итог: %d замен ---" % total)
    if fails:
        print("ОШИБКИ:")
        for f in fails:
            print("  " + f)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
