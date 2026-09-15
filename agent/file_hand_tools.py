# -*- coding: utf-8 -*-
"""ФАЙЛОВЫЕ ИНСТРУМЕНТЫ (file_hand_tools.py)
Инструменты для безопасного манипулирования файлами с бекапами и компиляционным контролем.
"""
import os
import shutil
import datetime
import subprocess
import sys
from pathlib import Path
import glob
import core
from core import log, REPO, BASE

# === Политика путей ===
# Разрешены: D:\AI\repo и D:\AI\tools\agent (с ограничениями)
# Запрещены: users.py, users.json, data\backup, .git, agent.pid, и др.

FORBIDDEN_NAMES = {"users.py", "users.json", "agent.pid"}
FORBIDDEN_DIRS = {"data\\backup", ".git"}

def _is_allowed(p: Path):
    """Проверка пути на соответствие политике безопасности."""
    try:
        # Разрешаем только абсолютные пути, которые мы резолвим
        abs_p = p.resolve()
        abs_str = str(abs_p)
        
        # 1. Проверка на запрещенные файлы по имени
        if abs_p.name in FORBIDDEN_NAMES:
            return False, f"защищённый путь: {abs_p.name}"
        
        # 2. Проверка на запрещенные директории
        for fdir in FORBIDDEN_DIRS:
            if fdir in abs_str:
                return False, f"защищённый путь: {fdir}"
        
        # 3. Проверка на принадлежность к разрешенным корням
        # Разрешен REPO
        if abs_str.startswith(str(REPO)):
            return True, ""
            
        # Разрешен BASE (D:\AI\tools\agent)
        if abs_str.startswith(str(BASE)):
            # Внутри agent разрешены: ui, dev, data\tmp, и *.py в корне agent
            # Проверяем sub-parts
            rel = abs_p.relative_to(BASE)
            
            # Если это файл в корне agent (.py)
            if len(rel.parts) == 1 and rel.suffix == ".py":
                return True, ""
            
            # Если это папка/файл в ui, dev, data/tmp
            parts = rel.parts
            if parts[0] in {"ui", "dev"}:
                return True, ""
            if parts[0] == "data" and len(parts) >= 2 and parts[1] == "tmp":
                return True, ""
            
            # Если путь в другом месте внутри BASE, но не запрещенный (например, core.py)
            # Но по спеке: "D:\AI\tools\agent (ui, dev, data\tmp, *.py дома)"
            # Это значит, что другие файлы в BASE могут быть запрещены или не указаны.
            # Будем придерживаться строгого списка из спеки.
            return False, f"путь вне разрешенных зон агента: {rel}"
            
        return False, f"путь вне разрешенных корней: {abs_p}"
    except Exception as e:
        return False, f"ошибка проверки пути: {e}"

def _create_backup(p: Path):
    r"""Создание бекапа в data\backup\pre_fs_<время>_<имя>"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = BASE / "data" / "backup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        backup_name = f"pre_fs_{timestamp}_{p.name}.bak"
        backup_path = backup_dir / backup_name
        
        shutil.copy2(p, backup_path)
        return backup_path
    except Exception as e:
        log(f"backup err: {e}")
        return None

def _compile_py(p: Path):
    """Компиляционный предохранитель для .py файлов."""
    try:
        # Используем sys.executable для запуска модуля py_compile
        result = subprocess.run([sys.executable, "-m", "py_compile", str(p)], 
                                capture_output=True, text=True, check=True)
        return True, ""
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip()
    except Exception as e:
        return False, str(e)

def fs_list(path=".", mask="*", **kw):
    """Список файлов (approval=False)"""
    try:
        p = Path(path).resolve()
        allowed, msg = _is_allowed(p)
        if not allowed: return msg
        if not p.is_dir(): return "путь не является директорией"
        
        files = list(p.glob(mask))
        if not files: return "пусто"
        
        out = []
        for f in files:
            out.append(f"{f.name} ({f.stat().st_size} bytes)")
        return "\n".join(out)
    except Exception as e:
        return f"ошибка: {e}"

def fs_write(path="", text="", **kw):
    """Запись файла целиком (approval=True)"""
    try:
        p = Path(path).resolve()
        allowed, msg = _is_allowed(p)
        if not allowed: return msg
        if not text: return "пустой текст"

        # Бекап
        backup_path = _create_backup(p) if p.exists() else None

        # Запись
        p.write_text(text, encoding="utf-8")

        # Компиляция
        if p.suffix == ".py":
            success, err = _compile_py(p)
            if not success:
                if backup_path: shutil.copy2(backup_path, p)
                return f"ошибка компиляции: {err}. Откат выполнен."

        return f"файл записан: {p}"
    except Exception as e:
        return f"ошибка при записи: {e}"

def fs_edit(path="", old="", new="", **kw):
    """Точечная правка (approval=True): old должен встретиться РАВНО ОДИН раз"""
    try:
        p = Path(path).resolve()
        allowed, msg = _is_allowed(p)
        if not allowed: return msg
        if not p.exists(): return "файл не найден"
        if not old or not new: return "нужны old и new"

        content = p.read_text(encoding="utf-8")
        
        # Поиск вхождений
        count = content.count(old)
        if count == 0:
            return f"ошибка: текст '{old[:20]}...' не найден"
        if count > 1:
            # Ищем позиции первых двух для цитирования
            idx1 = content.find(old)
            idx2 = content.find(old, idx1 + 1)
            
            # Чтобы дать цитату с номером строки, посчитаем строки
            lines = content.splitlines()
            line_num1, line_num2 = -1, -1
            curr = 1
            for l in lines:
                if old in l:
                    if line_num1 == -1: line_num1 = curr
                    else:
                        line_num2 = curr
                        break
                curr += 1
            return f"ошибка: текст найден {count} раза. Первые места: строка {line_num1}, строка {line_num2}. Требуется уникальность."

        # Бекап
        backup_path = _create_backup(p)

        # Правка
        new_content = content.replace(old, new, 1)
        p.write_text(new_content, encoding="utf-8")

        # Компиляция
        if p.suffix == ".py":
            success, err = _compile_py(p)
            if not success:
                if backup_path: shutil.copy2(backup_path, p)
                return f"ошибка компиляции: {err}. Откат выполнен."

        return f"файл отредактирован: {p}"
    except Exception as e:
        return f"ошибка при редактировании: {e}"

TOOLS = [
    {"name": "fs_list", "desc": "Список файлов (path, mask)", "params": {"path": "путь", "mask": "маска"}, "approval": False, "fn": fs_list},
    {"name": "fs_write", "desc": "Запись файла целиком (path, text)", "params": {"path": "путь", "text": "текст"}, "approval": True, "fn": fs_write},
    {"name": "fs_edit", "desc": "Точечная правка (path, old, new)", "params": {"path": "путь", "old": "текст", "new": "текст"}, "approval": True, "fn": fs_edit},
]
