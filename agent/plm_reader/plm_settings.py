import sys 
import os ; echo import json 
SETTINGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings') ; echo SETTINGS_FILE = os.path.join(SETTINGS_DIR, 'settings.json') 
CURRENT_SETTINGS_VERSION = 3 ; echo DEFAULT_SETTINGS = { 
'max_size_mb': 24, ; echo 'recurse': True, ; echo 'latest_only': True, ; echo 'depth': 0, 
'purge_keep': 2, ; echo 'auto_refresh': True, ; echo 'full': False, ; echo 'columns': ['Файл','Обозначение','Наименование','Материал','Объем, мм3'], 
'param_designation': ['ОБОЗНАЧЕНИЕ','OBOZNACHENIE','DESIGNATION','DESIGNATOR','PART_NUMBER'], ; echo 'param_name': ['НАИМЕНОВАНИЕ','NAME','PART_NAME','DESCRIPTION','TITLE'], ; echo 'param_material': ['PTC_MASTER_MATERIAL','MATERIAL','МАТЕРИАЛ'], ; echo 'folders': [], 
'exclude': [], ; echo 'db_dir': '', ; echo 'db_mirror': [], ; echo 'show_limit': 50000, 
} 
 
# -*- coding: utf-8 -*- ; echo import os ; echo import json 
SETTINGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings')  
SETTINGS_FILE = os.path.join(SETTINGS_DIR, 'settings.json')  
CURRENT_SETTINGS_VERSION = 3 
