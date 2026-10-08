# -*- coding: utf-8 -*-
"""plm_settings.py — настройки, миграции, пути."""
import os
import json
import datetime
import re
from plm_logger import log_line

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "db")
CACHE_FILE = os.path.join(DATA_DIR, "scan_cache.json")
DB_FILE = os.path.join(DATA_DIR, "plm_reader.db")

SETTINGS_DIR = os.path.join(HERE, "settings")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.json")
LOG_DIR = os.path.join(HERE, "log")
REPORTS_DIR = os.path.join(LOG_DIR, "reports")

CURRENT_SETTINGS_VERSION = 3

DEFAULT_SETTINGS = {
    "max_size_mb": 24,
    "recurse": True,
    "latest_only": True,
    "depth": 0,
    "purge_keep": 2,
    "auto_refresh": True,
    "full": False,
    "columns": ["Файл", "Обозначение", "Наименование", "Материал", "Объём, мм\u00b3",
                "Роль", "Родитель", "Ревизия", "Записей", "Версий", "Дата",
                "Создан", "Изменён", "Пользователь", "Версия Creo"],
    "param_designation": ["ОБОЗНАЧЕНИЕ", "OBOZNACHENIE", "DESIGNATION", "DESIGNATOR", "PART_NUMBER"],
    "param_name": ["НАИМЕНОВАНИЕ", "NAME", "PART_NAME", "DESCRIPTION", "TITLE"],
    "param_material": ["PTC_MASTER_MATERIAL", "MATERIAL", "МАТЕРИАЛ"],
    "folders": [],
}

