# -*- coding: utf-8 -*-
r"""ПРОГРАММЫ ДОМА И БАЗЫ (prog_tools.py)

Мост между ЕДИНЫМ СПИСКОМ ПРОГРАММ (`data\programs.json`) и агентом/витриной:
- `prog_list`   — что есть у дома, по группам (человек / Creo / ИИ / устаревшее) + живой статус;
- `prog_run`    — запустить ДВИЖОК в фоне (только у тех, где это разрешено) через `dev\prog_runner.py`,
                  который пишет «запущено в фоне» и «завершено …» в ОБЩИЙ ЖУРНАЛ РАБОТ (`core.job`);
- `prog_state`  — работает ли и что в его журнале;
- `bases_list`  — базы дома: размер, когда обновлялась, свои таблицы или чужие (правило: чужое — только чтение).

Окна (`.bat` с настройками) не подменяем — показываем путь: человек запускает их сам.
"""
import json, subprocess, sys, datetime
from pathlib import Path
import core
from core import log

AGENT = core.BASE / "agent"
PROGJSON = AGENT / "data" / "programs.json"
LOG_ROOT = Path(r"D:\AI\log")
JOBS_TAIL = 25


def _load():
    try:
        return json.loads(PROGJSON.read_text(encoding="utf-8"))
    except Exception as e:
        return {"groups": [], "programs": [], "error": "не читается %s: %s" % (PROGJSON, e)}


def _pid_alive(pid):
    try:
        out = subprocess.run(["tasklist", "/FI", "PID eq %d" % int(pid)],
                             capture_output=True, text=True, timeout=15)
        return str(int(pid)) in (out.stdout or "")
    except Exception:
        return False


def _running(p):
    """Живой признак программы: замок с PID (если он у неё есть)."""
    lk = p.get("lock")
    if not lk:
        return 0
    f = AGENT / lk
    try:
        txt = f.read_text(encoding="utf-8", errors="ignore")
        pid = int("".join(ch for ch in txt.strip().split()[0] if ch.isdigit()) or 0)
    except Exception:
        return 0
    return pid if (pid and _pid_alive(pid)) else 0


def _logfile(p):
    return LOG_ROOT / p["id"] / "run_last.txt"


def prog_list(group="", as_json=False, **kw):
    """Что есть у дома: по группам, с состоянием. group — human/creo/ai/legacy."""
    d = _load()
    groups = d.get("groups") or []
    progs = d.get("programs") or []
    if group:
        progs = [p for p in progs if p.get("group") == group]
    if as_json:
        out = []
        for p in progs:
            q = dict(p)
            q["pid"] = _running(p)
            q["logfile"] = str(_logfile(p))
            out.append(q)
        return {"groups": groups, "programs": out, "updated": d.get("updated")}
    lines = ["ПРОГРАММЫ ДОМА (всего %d; список: %s)" % (len(progs), PROGJSON)]
    for g in groups:
        if group and g["id"] != group:
            continue
        rows = [p for p in progs if p.get("group") == g["id"]]
        if not rows:
            continue
        lines.append("\n%s %s — %s" % (g.get("icon", ""), g["title"], g.get("note", "")))
        for p in rows:
            pid = _running(p)
            mark = "🟢 работает (PID %d)" % pid if pid else "⚪ готова"
            lines.append("  %s [%s] %s" % (mark, p.get("klass", "—"), p["title"]))
            lines.append("      движок: %s" % p.get("engine", "—"))
            if p.get("window"):
                lines.append("      окно: %s\\%s" % (p.get("cwd") or ".", p["window"]))
            lines.append("      журнал: %s" % (p.get("logs") or "не пишет"))
            lines.append("      паспорт: %s" % (p.get("readme") or "—"))
            lines.append("      состояние: %s" % p.get("status", "—"))
    if d.get("error"):
        lines.append("ОШИБКА СПИСКА: %s" % d["error"])
    return "\n".join(lines)


def prog_state(prog_id="", tail=20, **kw):
    """Работает ли программа сейчас и что в её журнале запуска."""
    d = _load()
    p = next((x for x in (d.get("programs") or []) if x["id"] == prog_id), None)
    if not p:
        ids = ", ".join(x["id"] for x in (d.get("programs") or []))
        return "нет программы %r. Есть: %s" % (prog_id, ids)
    pid = _running(p)
    out = ["%s: %s" % (p["title"], "РАБОТАЕТ (PID %d)" % pid if pid else "не запущена")]
    lf = _logfile(p)
    if lf.exists():
        txt = lf.read_text(encoding="utf-8", errors="replace").splitlines()[-int(tail or 20):]
        out.append("последний запуск (%s):" % lf)
        out += ["  " + x for x in txt]
    else:
        out.append("своего файла запуска нет (%s)" % lf)
    return "\n".join(out)


def prog_run(prog_id="", args="", **kw):
    """Запустить движок программы в фоне. Обёртка пишет в ОБЩИЙ ЖУРНАЛ РАБОТ (core.job)."""
    d = _load()
    p = next((x for x in (d.get("programs") or []) if x["id"] == prog_id), None)
    if not p:
        ids = ", ".join(x["id"] for x in (d.get("programs") or []))
        return "нет программы %r. Есть: %s" % (prog_id, ids)
    if p.get("group") == "legacy":
        return "«%s» — устаревшее, запуск из агента запрещён (см. _legacy\\README.md)" % p["title"]
    run = p.get("run")
    if not run:
        return ("у «%s» нет разрешённого запуска из агента: это делает человек своим окном %s\\%s"
                % (p["title"], p.get("cwd") or ".", p.get("window") or "—"))
    pid_now = _running(p)
    if pid_now:
        return "«%s» уже работает (PID %d) — смотри prog_state id=%s" % (p["title"], pid_now, p["id"])
    cwd = str(AGENT if (p.get("cwd") in (".", "", None)) else (AGENT / p["cwd"]))
    cmd = [x.replace("{}", args or "") for x in run]
    cmd = [x for x in cmd if x != ""]
    extra = [a for a in str(args or "").split() if a]
    if extra and not any("{}" in x for x in run):
        cmd += extra
    lf = _logfile(p)
    wrapper = [sys.executable, str(AGENT / "dev" / "prog_runner.py"), p["id"], cwd, str(lf)] + cmd
    try:
        pr = subprocess.Popen(wrapper, cwd=str(AGENT))
    except Exception as e:
        return "не удалось запустить «%s»: %s" % (p["title"], e)
    return ("«%s» запущена в фоне (PID %d). Смотреть: prog_state prog_id=%s; файл запуска: %s"
            % (p["title"], pr.pid, p["id"], lf))


def bases_list(as_json=False, **kw):
    """Базы дома: размер, когда обновлялась, свои таблицы или чужие."""
    items = [
        ("agent.sqlite", AGENT / "data" / "agent.sqlite", "своя",
         "память, знания (FTS5), пользователи, факты"),
        ("harvest.db", AGENT / "data" / "harvest.db", "своя",
         "индекс дома: models_raw, pairs, bom, facts_parser"),
        ("index.sqlite (Continue)", Path(r"D:\AI\continue\index\index.sqlite"),
         "ЧУЖАЯ — только чтение", "индекс редактора Continue (не наш)"),
        ("agent_20260821 (бэкап)", Path(r"D:\AI\repo\backup_db\agent_20260821_074452.sqlite"),
         "бэкап", "копия базы агента до чистки памяти"),
    ]
    rows = []
    for name, path, kind, what in items:
        if not path.exists():
            rows.append({"name": name, "path": str(path), "kind": kind, "what": what,
                         "mb": 0, "mtime": "нет файла", "tables": "-"})
            continue
        st = path.stat()
        try:
            import sqlite3
            c = sqlite3.connect("file:%s?mode=ro" % path.as_posix(), uri=True, timeout=5)
            nt = c.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
            c.close()
        except Exception as e:
            nt = "ошибка чтения: %s" % str(e)[:40]
        rows.append({"name": name, "path": str(path), "kind": kind, "what": what,
                     "mb": round(st.st_size / 1048576, 1),
                     "mtime": datetime.datetime.fromtimestamp(st.st_mtime).strftime("%d.%m.%Y %H:%M"),
                     "tables": nt})
    if as_json:
        return rows
    out = ["БАЗЫ ДОМА (чужое не трогаем; обновление — отдельной командой):"]
    for r in rows:
        out.append("• %s — %s МБ, таблиц: %s, обновлена %s (%s)"
                   % (r["name"], r["mb"], r["tables"], r["mtime"], r["kind"]))
        out.append("    %s" % r["path"])
        out.append("    внутри: %s" % r["what"])
    out.append("\nОБНОВИТЬ: индекс дома — prog_run prog_id=harvest; индекс знаний — index_run; "
               "PLM — plm_mine; состав — usage_build. Журнал работ — jobs_show.")
    return "\n".join(out)


def jobs_show(tail=JOBS_TAIL, **kw):
    """Общий журнал работ дома: «запущено в фоне» … «завершено …»."""
    return core.jobs_tail(int(tail or JOBS_TAIL))


TOOLS = [
    {"name": "prog_list", "desc": "Программы дома по группам: движок, окно, журнал, состояние",
     "params": {"group": "human/creo/ai/legacy", "as_json": "для витрины"}, "fn": prog_list},
    {"name": "prog_run", "desc": "Запустить движок программы В ФОНЕ (докладывает в общий журнал)",
     "params": {"prog_id": "имя программы", "args": "аргументы"}, "approval": True, "fn": prog_run},
    {"name": "prog_state", "desc": "Работает ли программа и что в её журнале запуска",
     "params": {"prog_id": "имя программы", "tail": "строк"}, "fn": prog_state},
    {"name": "bases_list", "desc": "Базы дома: размер, свежесть, свои/чужие таблицы",
     "params": {"as_json": "для витрины"}, "fn": bases_list},
    {"name": "jobs_show", "desc": "Общий журнал работ дома (запущено/завершено)",
     "params": {"tail": "строк"}, "fn": jobs_show},
]
