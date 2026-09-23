# -*- coding: utf-8 -*-
"""ШИМ к автономной программе `agent\\log_clean\\` (уборка логов по срокам хранения).

Движок и окно настроек переехали в свою папку:
    agent\\log_clean\\engine.py   — движок (scan / clean / retention)
    agent\\log_clean\\gui.py      — окно (log_clean_gui.bat)
Этот файл оставлен, чтобы старые вызовы из кода дома продолжали работать.

ВАЖНО про совместимость: прежний `log_clean.clean()` УДАЛЯЛ старые файлы навсегда, поэтому здесь
умолчание то же (`mode="delete"`). Безопасный режим (сначала в корзину) — в окне программы
или явным вызовом `clean(mode="trash")`.
"""
import importlib.util as _u
from pathlib import Path as _P

_SRC = _P(__file__).resolve().parent / "log_clean" / "engine.py"
_spec = _u.spec_from_file_location("log_clean_engine", _SRC)
_eng = _u.module_from_spec(_spec)
_spec.loader.exec_module(_eng)

LOG_ROOT = _eng.LOG_ROOT
RETENTION_FILE = _eng.RETENTION_FILE
DEFAULT_DAYS = _eng.DEFAULT_DAYS
get_retention = _eng.get_retention
save_retention = _eng.save_retention
is_locked = _eng.is_locked
scan = _eng.scan
trash_cleanup = _eng.trash_cleanup


def clean(root=None, mode="delete", days_default=DEFAULT_DAYS, report=True):
    """Совместимый вход: `clean()` — как раньше (удаление). Корзина — `clean(mode='trash')`."""
    return _eng.clean(root, mode, days_default, report)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(_SRC), run_name="__main__")