import os

content = """# -*- coding: utf-8 -*-
\"\"\"
АГЕНТ v13 — БИБЛИОТЕКА СКАНЕРА (scanner.py)
Чистая библиотека без управления состоянием. 
Управляется через harvest.py.
\"\"\"
import os
import re
import time
from pathlib import Path
from typing import Generator, List, Tuple, Optional

# Импорты из среды агента
try:
    from core import log, db, is_creo, is_excluded, read_roots
    from settings import get as settings_get
except ImportError:
    # Fallback для тестов
    def log(msg): print(msg)
    def db(): pass
    def is_creo(fn): return False
    def is_excluded(p, pats): return False
    def read_roots(): return []
    def settings_get(k): return None

class ScannerLibrary:
    def __init__(self):
        self.pats = self._get_pats()

    def _get_pats(self) -> List[str]:
        pats = []
        # Пытаемся найти исключения из файлов конфигурации
        for base in ["D:\\\\AI\\\\", "D:\\\\AI\\\\tools\\\\agent\\\\"]:
            f = Path(base) / "kb_exclude.txt"
            if f.exists():
                try:
                    lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
                    pats.extend([l.strip() for l in lines if l.strip() and not l.strip().startswith("#")])
                    break
                except:
                    pass
        return pats

    def scan_files_generator(self, root_path: str) -> Generator[dict, None, None]:
        \"\"\"Генератор метаданных файлов для потокового сканирования.\"\"\"
        rp = Path(root_path).resolve()
        if not rp.exists():
            return

        for dirpath, dirnames, filenames in os.walk(rp):
            # Фильтрация директорий (in-place)
            dirnames[:] = [d for d in dirnames if not is_excluded(os.path.join(dirpath, d), self.pats)]
            
            for fn in filenames:
                full_path = os.path.join(dirpath, fn)
                if is_excluded(full_path, self.pats):
                    continue
                
                try:
                    stat = os.stat(full_path)
                    yield {
                        "path": full_path,
                        "mtime": stat.st_mtime,
                        "size": stat.st_size,
                        "ext": os.path.splitext(fn)[1].lower(),
                        "name": fn
                    }
                except (OSError, PermissionError):
                    continue

    def scan_models(self, root_path: str) -> List[Tuple[str, str, str]]:
        \"\"\"Сканирование только Creo моделей.\"\"\"
        rp = Path(root_path).resolve()
        if not rp.exists():
            return []
        
        models = []
        for dirpath, dirnames, filenames in os.walk(rp):
            dirnames[:] = [d for d in dirnames if not is_excluded(os.path.join(dirpath, d), self.pats)]
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                if is_creo(fn) and not is_excluded(full, self.pats):
                    # m.group(1) из спеки
                    m = re.search(r"\\.(prt|asm|drw|frm|sec|lay)(?:\\.\\d+)?$", fn.lower())
                    ext = m.group(1) if m else ""
                    models.append((fn.lower(), ext, full))
        return models

    def get_duplicates(self) -> List[Tuple[str, int]]:
        \"\"\"Поиск дублей по имени в БД.\"\"\"
        c = db()
        try:
            rows = c.execute("SELECT name, COUNT(*) FROM models GROUP BY name HAVING COUNT(*) > 1 ORDER BY COUNT(*) DESC LIMIT 40").fetchall()
            return rows
        finally:
            c.close()

def init_db_schema():
    \"\"\"Инициализация таблиц (вызывается один раз при старте harvest).\"\"\"
    c = db()
    try:
        # Таблицы для файлов и FTS
        c.execute("CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY, mtime REAL, size INTEGER, hash TEXT, root TEXT, type TEXT)")
        c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS fts_index USING fts5(path UNINDEXED, content)")
        # Таблица для моделей
        c.execute("CREATE TABLE IF NOT EXISTS models(name TEXT, ext TEXT, path TEXT)")
        c.commit()
    finally:
        c.close()
"""

with open(r"D:\AI\tools\agent\scanner.py", "w", encoding="utf-8") as f:
    f.write(content)
print("scanner.py updated successfully")
