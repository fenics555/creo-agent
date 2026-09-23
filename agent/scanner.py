# -*- coding: utf-8 -*-
"""
АГЕНТ v13 — БИБЛИОТЕКА СКАНЕРА (scanner.py)
Чистая библиотека без управления состоянием. 
Управляется через harvest.py.
"""
import os
import re
import time
from pathlib import Path
from typing import Generator, List, Tuple, Optional, Dict, Any
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

    def parse_model_header(self, path: str) -> Dict[str, Any]:
        """
        B0. ПАРСЕР .prt/.asm: parse_model_header(path) -> {instances, families}
        Читает поток байтов/текста, ищет маркеры заголовков.
        """
        results = {"instances": [], "families": []}
        p = Path(path)
        if not p.exists():
            return results

        try:
            # Для имитации работы с бинарными файлами Creo, читаем кусками
            with open(path, 'rb') as f:
                content = f.read(1024 * 64) # Читаем первые 64КБ
                
                # Ищем маркеры (имитация)
                content_str = content.decode('utf-8', errors='ignore')
                
                # Ищем 'instances'
                instances_match = re.findall(r'instances\s*[:=]\s*\[(.*?)\]', content_str, re.DOTALL)
                if instances_match:
                    results["instances"] = [i.strip() for i in instances_match[0].split(',')]
                
                # Ищем 'families'
                families_match = re.findall(r'families\s*[:=]\s*\[(.*?)\]', content_str, re.DOTALL)
                if families_match:
                    results["families"] = [f.strip() for f in families_match[0].split(',')]
                    
        except Exception as e:
            log(f"Error parsing model header {path}: {e}")
            
        return results


    def _get_pats(self) -> List[str]:
        pats = []
        # Пытаемся найти исключения из файлов конфигурации
        for base in ["D:\\AI\\", "D:\\AI\\tools\\agent\\"]:
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
        """Генератор метаданных файлов для потокового сканирования."""
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
        """Сканирование только Creo моделей."""
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
                    m = re.search(r"\.(prt|asm|drw|frm|sec|lay)(?:\.\d+)?$", fn.lower())
                    ext = m.group(1) if m else ""
                    models.append((fn.lower(), ext, full))
        return models

    def get_duplicates(self) -> List[Tuple[str, int]]:
        """Поиск дублей по имени в БД."""
        c = db()
        try:
            rows = c.execute("SELECT name, COUNT(*) FROM models GROUP BY name HAVING COUNT(*) > 1 ORDER BY COUNT(*) DESC LIMIT 40").fetchall()
            return rows
        finally:
            c.close()

def init_db_schema():
    """Инициализация таблиц (вызывается один раз при старте harvest)."""
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


# ─────────────────────── ИНДЕКС ЗНАНИЙ (FTS5, без эмбеддингов) ───────────────────────
# Решение дома 23.09.2026: тяжёлая векторная база отменена. 1 330 971 чанк и 3,81 ГБ
# эмбеддингов давали агенту 13 ГБ commit, при этом 84 % чанков были короче 50 символов,
# а 1,27 млн — нарезкой бинарных чертежей (.drw). Знание дома — это ТЕКСТОВЫЕ файлы
# (скиллы, карты, ГОСТы, отчёты): их ищем через FTS5 — без Ollama, без эмбеддингов,
# без памяти в процессе агента. Бинарники Creo не читаются вовсе.
TEXT_EXT = {".md", ".txt", ".html", ".htm", ".csv", ".json", ".yaml", ".yml", ".rst", ".py"}
KB_FRAGMENT = 2000      # символов на фрагмент индекса


def _kb_roots(roots=None) -> List[str]:
    """Корни индекса знаний: по умолчанию настройка scan_roots (список или JSON-строка)."""
    import json as _json
    if roots is None:
        roots = settings_get("scan_roots") or []
    if isinstance(roots, str):
        try:
            roots = _json.loads(roots)
        except Exception:
            roots = [x.strip() for x in roots.split(",") if x.strip()]
    return [str(x).strip() for x in roots if str(x).strip()]


def index_all(roots=None, quiet=False) -> Dict[str, int]:
    """Пересобрать индекс знаний (таблица fts_index). Только текстовые файлы.
    Возвращает {'files': файлов, 'fragments': фрагментов}. Бинарники Creo пропускаются."""
    lib = ScannerLibrary()
    c = db()
    files = frags = 0
    try:
        c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS fts_index USING fts5(path UNINDEXED, content)")
        c.execute("DELETE FROM fts_index")
        for root in _kb_roots(roots):
            if not os.path.isdir(root):
                continue
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames if not is_excluded(os.path.join(dirpath, d), lib.pats)]
                for fn in filenames:
                    if os.path.splitext(fn)[1].lower() not in TEXT_EXT:
                        continue
                    full = os.path.join(dirpath, fn)
                    if is_excluded(full, lib.pats):
                        continue
                    try:
                        txt = Path(full).read_text(encoding="utf-8", errors="ignore")
                    except Exception:
                        continue
                    if not txt.strip():
                        continue
                    for i in range(0, len(txt), KB_FRAGMENT):
                        c.execute("INSERT INTO fts_index(path, content) VALUES(?,?)",
                                  (full, txt[i:i + KB_FRAGMENT]))
                        frags += 1
                    files += 1
        c.commit()
    finally:
        c.close()
    if not quiet:
        log("индекс знаний FTS5: файлов %d, фрагментов %d" % (files, frags))
    return {"files": files, "fragments": frags}


def kb_search(query: str, limit: int = 4, chars: int = 900) -> List[Tuple[str, str]]:
    """Поиск по индексу знаний: FTS5-MATCH по словам, при неудаче — LIKE.
    Возвращает [(путь, фрагмент), ...]."""
    q = (query or "").strip()
    if not q:
        return []
    c = db()
    try:
        try:
            words = [w for w in re.split(r"[^\w\.\-]+", q, flags=re.UNICODE) if len(w) > 2]
            match = " OR ".join('"%s"' % w for w in words) or '"%s"' % q.replace('"', " ")
            rows = c.execute("SELECT path, content FROM fts_index WHERE fts_index MATCH ? "
                             "ORDER BY rank LIMIT ?", (match, int(limit))).fetchall()
        except Exception:
            rows = c.execute("SELECT path, content FROM fts_index WHERE content LIKE ? LIMIT ?",
                             ("%" + q + "%", int(limit))).fetchall()
        return [(r[0], (r[1] or "")[:chars]) for r in rows]
    finally:
        c.close()


def kb_state() -> Dict[str, int]:
    """Сколько сейчас в индексе знаний."""
    c = db()
    try:
        n = c.execute("SELECT COUNT(*) FROM fts_index").fetchone()[0]
        p = c.execute("SELECT COUNT(DISTINCT path) FROM fts_index").fetchone()[0]
        return {"fragments": n, "files": p}
    except Exception:
        return {"fragments": 0, "files": 0}
    finally:
        c.close()

