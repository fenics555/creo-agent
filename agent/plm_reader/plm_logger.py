# -*- coding: utf-8 -*-
"""plm_logger.py — единый логгер для всех модулей."""
import os
import datetime

# В новых версиях LOG_DIR берется из plm_settings, 
# но для инициализации логгера нам нужно знать, куда писать.
# Мы будем импортировать LOG_DIR из plm_settings.

def log_line(text, log_dir=None):
    """Одна строка в общий лог инструмента."""
    try:
        if log_dir is None:
            # Если не передан, пробуем найти через plm_settings
            try:
                from plm_settings import LOG_DIR
                log_dir = LOG_DIR
            except ImportError:
                # Фолбек, если модули еще не связаны
                log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log")
        
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, "plm_reader.log"), "a", encoding="utf-8") as f:
            f.write("%s  %s\\n" % (datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"), text))
    except Exception:
        pass
