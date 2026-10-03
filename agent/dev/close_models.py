# -*- coding: utf-8 -*-
r"""dev\close_models.py - ЗАКРЫТЬ открытые модели в Creo БЕЗ сохранения.

Нужно перед прогоном записи на копию: пока в сессии открыта модель с тем же стемом,
`file:open` не переключает окно (инцидент 03.10.2026).
"""
import io
import json
import sys
import time
from pathlib import Path

AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))


def _names(data):
    """Имена моделей из ответа `file:list`.

    ЖИВАЯ ЦИТАТА (`rename_tools.py:89`): `data` — СЛОВАРЬ, а `files` — его ключ
    `(j.get("data") or {}).get("files") or []`. Прежняя версия ждала список и
    выдавала имя «files» вместо имён моделей (RC 1, 03.10.2026). Поэтому разбираем
    оба вида: словарь с ключом `files`, список и строку."""
    if isinstance(data, dict):
        data = data.get("files") or []
    if isinstance(data, dict):          # files может быть словарём {имя: ...}
        data = list(data.keys())
    if isinstance(data, str):
        data = [data]
    out = []
    for m in (data or []):
        if isinstance(m, str) and m.strip():
            out.append(m.strip())
        elif isinstance(m, dict):
            n = m.get("name") or m.get("file") or m.get("filename")
            if n:
                out.append(str(n))
    return out


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    import creo_tools as CT
    j = CT.creo_call("file", "list", {}, 20)
    names = _names(j.get("data"))
    print("открыто до (%d): %s" % (len(names), ", ".join(names) or "—"))
    # ЖИВАЯ ПРАВКА 03.10.2026: `file:close_window` отвечает «успех», но НЕ убирает модель
    # из сессии. Убирает только `file:erase` по имени — он и выгружает, и не пишет на диск.
    for n in names:
        je = CT.creo_call("file", "erase", {"file": n}, 30)
        print("  erase %s -> ok=%s" % (n, CT.ok(je)))
        time.sleep(0.5)
    time.sleep(2)
    j2 = CT.creo_call("file", "list", {}, 20)
    left = _names(j2.get("data"))
    print("открыто после (%d): %s" % (len(left), ", ".join(left) or "—"))
    print("ВЕРДИКТ: %s" % ("сессия чиста" if not left else "в сессии остались: %s" % left))
    return 0 if not left else 1


if __name__ == "__main__":
    sys.exit(main())