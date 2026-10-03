# -*- coding: utf-8 -*-
r"""creo_find.py — тонкая обёртка над ОБЩИМ поиском установки Creo.

Сам поиск живёт ОДИН раз на дом: `agent\agent\creo_path.py`
(приоритет: бат запуска → реестр PTC → диск → настройки).
Проверить:  python creo_find.py        — путь Common Files в stdout
            python creo_find.py -v     — плюс откуда взят (в stderr)
Код возврата: 0 — найдено, 1 — нет.

02.10.2026: из этого файла удалены собственные копии поиска (они разошлись бы
с общим модулем — это и было нарушением «одна база, одно место»).
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_AGENT = os.path.dirname(_HERE)                     # ...\tools\agent
for _p in (os.path.join(_AGENT, "agent"), _AGENT):  # папка общих модулей + сам корень
    if _p not in sys.path:
        sys.path.insert(0, _p)

import creo_path as _shared          # noqa: E402


def find(verbose=False):
    """Единая точка поиска: общий модуль дома. Возвращает (common, откуда)."""
    com, par, why = _shared.find()
    if verbose:
        sys.stderr.write("creo_find: %s (%s) | parametric=%s\n" % (com, why, par))
    return com, why


def main():
    com, why = find(verbose=("-v" in sys.argv))
    print(com or "")
    return 0 if com else 1


if __name__ == "__main__":
    sys.exit(main())