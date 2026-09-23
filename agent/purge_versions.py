# -*- coding: utf-8 -*-
"""ШИМ к автономной программе `agent\\purge_versions\\` (чистка версий Creo).

Движок переехал в свою папку (`purge_versions\\engine.py`), потому что чистка версий — это
самостоятельная программа: свои настройки, свои логи (`D:\\AI\\log\\purge_versions`), своё окно (`purge_gui.bat`).
Этот файл оставлен ТОЛЬКО чтобы агент (`http_handlers.py`, `purge_tools.py`) продолжал работать как раньше.
Править логику — в `purge_versions\\engine.py`, не здесь.
"""
import importlib.util as _u
from pathlib import Path as _P

_SRC = _P(__file__).resolve().parent / "purge_versions" / "engine.py"
_spec = _u.spec_from_file_location("purge_versions_engine", _SRC)
_eng = _u.module_from_spec(_spec)
_spec.loader.exec_module(_eng)

Lock = _eng.Lock
get_groups = _eng.get_groups
preview = _eng.preview
execute = _eng.execute
EXTS = _eng.EXTS
LOG_DIR = _eng.LOG_DIR
PROG_DIR = _eng.PROG_DIR

if __name__ == "__main__":
    _eng.main()