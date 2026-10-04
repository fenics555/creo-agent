# -*- coding: utf-8 -*-
"""fix_settings_types.py — ПОЧИНИТЬ ТИПЫ НАСТРОЕК (слово владельца «исправляй всё»).

ЖИВАЯ НАХОДКА 03.10.2026 (audit_all.py): четыре настройки лежат в config.json не того типа,
что объявлено в REGISTRY:
    night_hour        = '0'   (строка) — ждали int; читает agent_sched.py
    ollama_max_models = '4'   (строка) — ждали int; читает loop.py
    fleet_autocommit / parallel_tools / stream_ui = 1 (число) — ждали bool
Приведение делает САМ settings.set_val — он знает типы из REGISTRY. Мы только перевызываем
текущее значение через него, поэтому логика приведения не дублируется.
Результат печатается по каждой настройке ДО и ПОСЛЕ — с живыми типами.
"""
import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))

import settings as ST  # noqa: E402


def main():
    print("файл: %s" % ST.CONFIG_FILE)
    print("=" * 78)
    d = ST._raw()
    fixed = []
    for space, k, name, typ, defl, desc, ui in ST.REGISTRY:
        if k not in d:
            continue
        v = d[k]
        want = None
        if typ == "int" and isinstance(v, str) and v.strip().lstrip("-").isdigit():
            want = int(v.strip())
        elif typ == "bool" and isinstance(v, int) and not isinstance(v, bool):
            want = bool(v)
        if want is None:
            continue
        print("%-22s было %-6r (%s) → станет %-6r (%s)"
              % (k, v, type(v).__name__, want, typ))
        ST.set_val(k, want)
        fixed.append(k)
    print("=" * 78)
    print("исправлено настроек: %d %s" % (len(fixed), fixed if fixed else ""))
    # Проверка: перечитать файл и убедиться, что типы стали верными
    d2 = ST._raw()
    bad = []
    for space, k, name, typ, defl, desc, ui in ST.REGISTRY:
        v = d2.get(k, defl)
        if typ == "int" and isinstance(v, str):
            bad.append((k, "строка вместо int"))
        elif typ == "bool" and isinstance(v, int) and not isinstance(v, bool):
            bad.append((k, "число вместо bool"))
    print("осталось расхождений по типу: %d %s" % (len(bad), bad if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())