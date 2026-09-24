# -*- coding: utf-8 -*-
r"""
ТРАНСФОРМЕР v12 — БЛОК ЗНАНИЙ (knowledge_tools.py)
Векторный поиск по БЗ, чтение файлов, сохранение скиллов.
"""
import os
import users as _us

import threading
from pathlib import Path
import core
from core import log, REPO
import settings

try:
    import scanner
except Exception:
    scanner = None


def tool_search(query="", **kw):
    """Поиск по индексу знаний (FTS5 по ТЕКСТОВЫМ файлам: скиллы, карты, ГОСТы, отчёты).
    Тяжёлая векторная матрица (1,33 млн чанков, 3,81 ГБ эмбеддингов, 84 % мусора из
    бинарных .drw) удалена 23.09.2026: ищем без Ollama, без эмбеддингов, без памяти."""
    if not query:
        return "пустой запрос"
    if scanner is None:
        return "сканер недоступен"
    try:
        rows = scanner.kb_search(query, limit=settings.get("top_chunks") or 4,
                                 chars=settings.get("chunk_chars") or 900)
    except Exception as e:
        return "ошибка поиска: %s" % e
    if not rows:
        return ("в индексе знаний пусто или ничего не найдено. Пересобрать: "
                "python -c \"import scanner; scanner.index_all()\"")
    return "\n\n".join("[%d] %s\n%s" % (n + 1, p, t) for n, (p, t) in enumerate(rows))

READ_MAX_BYTES = 2 * 1024 * 1024  # не тянем в промт файлы больше 2 МБ

def _inside(p, root):
    try:
        p.relative_to(root); return True
    except ValueError:
        return False

def tool_read(path="", **kw):
    import threading, users as _us
    _p = os.path.abspath(path or "")
    _roots = [os.path.abspath(x) for x in (list(settings.get("scan_roots") or [])
              + [x.strip() for x in str(settings.get("read_roots") or "").split(";") if x.strip()]
              + [str(core.REPO), str(core.BASE)])]
    _inside = any(_p.startswith(r + os.sep) or _p == r for r in _roots)
    if not _inside:
        _cl = getattr(threading.current_thread(), "_tokclient", None)
        if not (_cl and _us.is_admin(_cl)):
            return ("🛔 чтение вне белых корней запрещено: разрешены scan_roots, репо и папка агента. "
                    "Попроси администратора или читай из разрешённых корней (правило безопасности волны G).")
    if not path: return "укажите path"
    p = Path(path).resolve()
    if not p.exists(): return "нет файла %s" % path
    try:
        sz = p.stat().st_size
    except OSError:
        return "нет доступа к файлу %s" % path
    if sz > READ_MAX_BYTES:
        return "файл слишком большой: %d КБ (лимит %d КБ)" % (sz // 1024, READ_MAX_BYTES // 1024)
    return p.read_text(encoding="utf-8", errors="ignore")[:6000]

def tool_skills_map(domain="", find="", rebuild=False, **kw):
    """КАРТА СКИЛЛОВ (заряд знаний): что есть в репо и когда брать.
    domain — домен (creo, pdf, plm, ...), find — подстрока в пути/описании, rebuild — пересобрать карту."""
    if rebuild:
        import subprocess, sys
        r = subprocess.run([sys.executable, str(core.BASE / "agent" / "dev" / "skills_charge.py")],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           cwd=str(core.BASE / "agent"), timeout=180)
        return "карта пересобрана:\n" + (r.stdout or "") + (r.stderr or "")
    p = REPO / "SKILL_CHARGE.md"
    if not p.exists():
        return ("карты ещё нет. Собрать: skills_map(rebuild=true) или "
                "python dev\\skills_charge.py")
    txt = p.read_text(encoding="utf-8", errors="ignore")
    dom, fnd = (domain or "").strip().lower(), (find or "").strip().lower()
    if not dom and not fnd:
        heads = [l for l in txt.splitlines() if l.startswith("## ")]
        return "ДОМЕНЫ СКИЛЛОВ (уточни domain или find):\n" + "\n".join(heads)
    cur, out = "", []
    for line in txt.splitlines():
        if line.startswith("## "):
            cur = line[3:].strip()
            continue
        if not line.startswith("- "):
            continue
        if (dom and dom in cur.lower()) and (fnd in line.lower() if fnd else True):
            out.append("[%s] %s" % (cur, line[2:]))
    if not out:
        return "по запросу ничего нет: domain=%r find=%r" % (domain, find)
    return "НАЙДЕНО СКИЛЛОВ: %d\n%s" % (len(out), "\n".join(out[:60]))


def tool_save(name="", content="", **kw):
    if not name or not content: return "нужны name и content"
    p = REPO / ("SKILL_" + name + ".md")
    p.write_text(content, encoding="utf-8")
    if scanner: threading.Thread(target=scanner.index_all, daemon=True).start()
    return "скилл сохранён: %s, переиндексация запущена" % p
    
TOOLS = [
    {"name": "search_kb", "desc": "Поиск по базе знаний КБ (скиллы, ГОСТы, docs)", "params": {"query": "запрос"}, "approval": False, "fn": tool_search},
    {"name": "skills_map", "desc": "Карта скиллов репо: что есть (domain/find), когда брать", "params": {"domain": "домен: creo, pdf, plm…", "find": "подстрока", "rebuild": "пересобрать карту"}, "approval": False, "fn": tool_skills_map},
    {"name": "read_file", "desc": "Прочитать файл целиком (до 6000 симв.)", "params": {"path": "полный путь"}, "approval": False, "fn": tool_read},
    {"name": "save_skill", "desc": "Сохранить новый скилл в базу знаний", "params": {"name": "имя", "content": "markdown"}, "approval": True, "fn": tool_save},
]