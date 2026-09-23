# -*- coding: utf-8 -*-
"""ШИМ к окну автономной программы `agent\\purge_versions\\` (ЧИСТИЛЬЩИК).

Настоящее окно: `python agent\\purge_versions\\gui.py` (ярлык — `purge_versions\\purge_gui.bat`).
Править интерфейс — в `purge_versions\\gui.py`, не здесь.
"""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parent / "purge_versions" / "gui.py"),
               run_name="__main__")