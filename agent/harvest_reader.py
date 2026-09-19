# -*- coding: utf-8 -*-
"""harvest_reader.py: read-only доступ к harvest.db."""
import sqlite3
import os
from pathlib import Path

# Путь к harvest.db (берем из agent/data/harvest.db)
HARVEST_DB = Path(r"D:\AI\tools\agent\data\harvest.db")

def get_connection():
    """Возвращает read-only соединение."""
    # Используем URI для mode=ro
    return sqlite3.connect(f"file:{HARVEST_DB}?mode=ro", uri=True)

def pair_for(stem):
    """(pdf_path, свежесть по mtime pdf против drw) для stem."""
    if not HARVEST_DB.exists():
        return None
    
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # Ищем модель, которая содержит stem
        cursor.execute("SELECT model, pdf_path FROM pairs WHERE model LIKE ?", (f"%{stem}%",))
        row = cursor.fetchone()
        if not row:
            return None
        
        model_name, pdf_path = row
        pdf_p = Path(pdf_path)
        
        if not pdf_p.exists():
            return (pdf_path, False)
        
        pdf_mtime = pdf_p.stat().st_mtime
        
        # Ищем drw/prt в той же папке. 
        # Базовое имя берем из pdf_path (без расширения .pdf)
        base_name = pdf_p.stem
        drw_mtime = 0
        
        # Проверяем расширения. drw, prt, asm.
        # Также учитываем префикс m- как в pdf_tools.py
        for ext in ['.drw', '.prt', '.asm']:
            # 1. Прямое совпадение: base.ext
            for p in pdf_p.parent.glob(f"{base_name}{ext}"):
                drw_mtime = p.stat().st_mtime
                break
            if drw_mtime > 0: break
            
            # 2. С префиксом m-: m-base.ext
            for p in pdf_p.parent.glob(f"m-{base_name}{ext}"):
                drw_mtime = p.stat().st_mtime
                break
            if drw_mtime > 0: break

        return (pdf_path, pdf_mtime >= drw_mtime)
    except Exception:
        return None
    finally:
        conn.close()

def pdf_paths(name):
    """Список путей к pdf для имени."""
    if not HARVEST_DB.exists():
        return []
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT pdf_path FROM pairs WHERE model LIKE ?", (f"%{name}%",))
        return [r[0] for r in cursor.fetchall()]
    except Exception:
        return []
    finally:
        conn.close()

def get_verdict(name):
    """/pdfstatus вердикт: актуален / устарел / нет pdf / харвест спит."""
    if not HARVEST_DB.exists():
        return "харвест спит"
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT model, pdf_path FROM pairs WHERE model LIKE ?", (f"%{name}%",))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return "нет pdf"
        
        # Используем pair_for для вычисления свежести
        res = pair_for(name)
        if not res:
            return "нет pdf"
        
        pdf_path, is_fresh = res
        return "актуален" if is_fresh else "устарел"
        
    except sqlite3.OperationalError as e:
        if "locked" in str(e).lower():
            return "харвест спит"
        return "нет pdf"
    except Exception:
        return "нет pdf"

def get_registry_entries(root_filter=None):
    """Для /pdfregistry. Возвращает список словарей с данными."""
    if not HARVEST_DB.exists():
        return []
    
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = "SELECT model, pdf_path FROM pairs"
        cursor.execute(query)
        rows = cursor.fetchall()
        
        entries = []
        for model_name, pdf_path in rows:
            p = Path(pdf_path)
            if root_filter and not str(p.resolve()).startswith(str(Path(root_filter).resolve())):
                continue
            
            # Для каждого входа считаем свежесть
            # Но pair_for принимает stem. Нам нужно найти drw mtime для этой модели.
            # Чтобы не делать тысячи запросов, сделаем упрощенно.
            
            # В идеале: за один проход собрать все файлы в словаре по папке.
            # Но для начала сделаем через pair_for для каждой строки (медленно, но надежно).
            # На самом деле, pair_for принимает stem. 
            # Если model_name - '1040.drw.1', stem - '1040'
            
            # Давайте попробуем извлечь stem из model_name
            # model_name: '1040-954-35.drw.1' -> stem: '1040-954-35'
            parts = model_name.split('.')
            stem = parts[0]
            
            # Чтобы не рекурсивно вызывать pair_for (который опять лезет в БД),
            # мы можем использовать данные из этой же строки, если они есть.
            # Но у нас в БД нет mtime drw.
            # Для /pdfregistry в спеке: "отдаёт вердикты парами с головой и фильтром по корню"
            # Мы вычислим свежесть на лету.
            
            res = pair_for(stem)
            if not res:
                verdict = "нет pdf"
                pdf_mtime = 0
            else:
                pdf_path_found, is_fresh = res
                verdict = "актуален" if is_fresh else "устарел"
                # Нам нужно mtime pdf для entry
                try:
                    pdf_mtime = Path(pdf_path_found).stat().st_mtime
                except:
                    pdf_mtime = 0
            
            entries.append({
                "model": model_name,
                "pdf": pdf_path,
                "verdict": verdict,
                "pdf_mtime": pdf_mtime
            })
        return entries
    except Exception:
        return []
    finally:
        conn.close()
