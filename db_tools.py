# -*- coding: utf-8 -*-
"""АГЕНТ v15 — БАЗЫ ДАННЫХ (db_tools.py): полное состояние хранилищ + три индексации."""
import os, sys, datetime, subprocess
import core

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))


def _q(c, sql):
    try:
        return c.execute(sql).fetchall()
    except Exception:
        return []


def _fmt_ts(ts):
    if not ts:
        return "никогда"
    d = datetime.datetime.fromtimestamp(ts)
    days = (datetime.datetime.now() - d).days
    return d.strftime("%m-%d %H:%M") + (" (сегодня)" if days == 0 else " (%d дн.)" % days)


def _count_dir(path):
    try:
        return len([f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))])
    except Exception:
        return 0


def db_state(verbose=0):
    c = core.db()
    f = (_q(c, "SELECT COUNT(*), MAX(mtime) FROM files") or [(0, None)])[0]
    chunks_n = (_q(c, "SELECT COUNT(*) FROM chunks") or _q(c, "SELECT COUNT(*) FROM fragments") or [(0,)])[0][0]
    links_n = (_q(c, "SELECT COUNT(*) FROM usage") or _q(c, "SELECT COUNT(*) FROM bom") or [(0,)])[0][0]
    names_n = (_q(c, "SELECT COUNT(DISTINCT parent) FROM usage") or [(0,)])[0][0]
    roots_n = (_q(c, "SELECT COUNT(*) FROM usage WHERE parent NOT IN (SELECT child FROM usage)") or [(0,)])[0][0]
    hist_n = (_q(c, "SELECT COUNT(*) FROM history") or [(0,)])[0][0]
    fb_n = (_q(c, "SELECT COUNT(*) FROM feedback") or [(0,)])[0][0]
    roots_list = [r[0] for r in _q(c, "SELECT parent FROM usage WHERE parent NOT IN (SELECT child FROM usage) LIMIT 10")]
    c.close()
    files_n, files_ts = f[0], f[1]
    bak_n = _count_dir(os.path.join(AGENT_DIR, "data", "backups"))
    pdf_n = _count_dir(os.path.join(AGENT_DIR, "data", "pdfcache"))
    jlines = 0
    try:
        jf = core.REPO / "Трейлы" / "TRAIL_JOURNAL.md"
        if jf.exists():
            jlines = len(jf.read_text(encoding="utf-8", errors="ignore").splitlines())
    except Exception:
        pass
    stale = bool(files_ts) and (datetime.datetime.now() - datetime.datetime.fromtimestamp(files_ts)).days > 3
    v_files = "пусто, наполни сканом" if not files_n else ("устарело, обнови скан" if stale else "актуально")
    v_chunks = "пусто, переиндексируй" if not chunks_n else "актуально"
    v_links = "пусто, пересобери" if not links_n else ("пересобери связи" if (not names_n or not roots_n) else "актуально")
    v_trails = "пусто, никто не работал" if not jlines else "актуально"
    out = ["🗄 СОСТОЯНИЕ БАЗ ДАННЫХ (полное):"]
    out.append("1. Файловый индекс: %d строк; скан %s → %s" % (files_n, _fmt_ts(files_ts), v_files))
    out.append("2. База знаний: %d фрагментов → %s" % (chunks_n, v_chunks))
    out.append("3. База связей: %d связей; имён %d; корней %d → %s" % (links_n, names_n, roots_n, v_links))
    out.append("4. Трейлы: журнал %d строк → %s" % (jlines, v_trails))
    out.append("5. История диалогов: %d; feedback: %d → ОК" % (hist_n, fb_n))
    out.append("6. Бэкапы sqlite: %d; pdf-кэш: %d → ОК" % (bak_n, pdf_n))
    bad = [l for l in out[1:] if not l.endswith("актуально")]
    out.append("Все базы актуальны." if not bad else "Требуют внимания: " + "; ".join(bad) + " — нажми кнопку индексации этого пункта.")
    if verbose:
        out.append("")
        out.append("ПОЛНАЯ ВЫГРУЗКА:")
        out.append("база sqlite: %s (%.1f МБ)" % (os.path.join(AGENT_DIR, "data", "agent.sqlite"),
                                                 os.path.getsize(os.path.join(AGENT_DIR, "data", "agent.sqlite")) / 1048576.0))
        out.append("корни деревьев (первые 10): %s" % (", ".join(roots_list) or "нет"))
        out.append("pdfcache: %d файлов; backups: %d копий" % (pdf_n, bak_n))
        return "\n".join(out)
    out.append("[DETAILS:dbfull]полная выгрузка по хранилищам[/DETAILS]")
    return "\n".join(out)


def db_index_models():
    subprocess.Popen([sys.executable, "-c", "import scanner; scanner.scan_models()"], cwd=AGENT_DIR)
    return {"msg": "скан 3D-моделей запущен в фоне; состояние — db_state или models_stats"}


def db_index_kb():
    subprocess.Popen([sys.executable, "-c", "import scanner; scanner.index_all()"], cwd=AGENT_DIR)
    return {"msg": "переиндексация базы знаний запущена в фоне; состояние — db_state или index_state"}


def db_index_links():
    subprocess.Popen([sys.executable, "-c", "import usage_tools; usage_tools.build_usage(True)"], cwd=AGENT_DIR)
    return {"msg": "пересбор базы связей запущен в фоне (тяжёлый); состояние — db_state или usage_state"}


TOOLS = [
    {"name": "db_state", "desc": "Полное состояние всех баз: файлы, чанки, связи, трейлы, история, бэкапы", "params": {"verbose": "0 кратко / 1 полная выгрузка"}, "fn": db_state},
    {"name": "db_index_models", "desc": "Запустить скан 3D-моделей в фоне (файловый индекс)", "params": {}, "fn": db_index_models},
    {"name": "db_index_kb", "desc": "Запустить переиндексацию базы знаний в фоне", "params": {}, "fn": db_index_kb},
    {"name": "db_index_links", "desc": "Запустить пересбор базы связей в фоне (тяжёлый, ночью)", "params": {}, "fn": db_index_links},
]