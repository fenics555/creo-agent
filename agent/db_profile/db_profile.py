# -*- coding: utf-8 -*-
r"""db_profile — профиль баз данных дома (Волна 1.1 плана, читающий).

Показывает, ЧТО занимает место: по каждой таблице — строк, оценка байт (dbstat, иначе
page_count), и признак «мозг» (пишет агент: chat/history/trail/…) против «свод»
(models/files/bom/fts — данные, которые по канону должны жить в локальной db\ инструмента).

ТОЛЬКО ЧТЕНИЕ (mode=ro) — на живой БД безопасен, ничего не пишет и не меняет.
Код возврата: 0 — всё прочитано · 2 — базы нет (нечего профилировать).

Запуск:  db_profile.py [путь_к_базе ...]      (по умолчанию — agent.sqlite + harvest.db из настроек)
         db_profile.py --json                 (машиночитаемо)
Пути к базам — из настроек settings\\settings.json (ключ dbs), либо аргументами. Абс. пути
в коде нет (закон канона №2): базы ищем по признаку относительно папки инструмента.
"""
import io
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
AGENT = HERE.parent                              # tools\\agent  (инструмент лежит в подпапке)
DATA = AGENT / "data"

# Зоны общей базы (из инвентаризации Волны 1): мозг пишет агент, свод — данные инструментов.
BRAIN = {"chat", "history", "trail_problems", "trail_scans", "skill_usage",
         "role_deny", "plm_statuses", "facts"}


def settings():
    d = {}
    sf = HERE / "settings" / "settings.json"
    try:
        if sf.exists():
            d = json.loads(sf.read_text(encoding="utf-8"))
    except Exception:
        d = {}
    return d


def default_dbs():
    """Базы по умолчанию: общая агента + чесалка. Пути относительные от data\\."""
    s = settings()
    out = []
    for rel in (s.get("dbs") or ["data/agent.sqlite", "data/harvest.db"]):
        p = (AGENT / rel) if not os.path.isabs(rel) else Path(rel)
        out.append(p)
    return out


def human(n):
    for u in ("Б", "КБ", "МБ", "ГБ"):
        if n < 1024 or u == "ГБ":
            return "%.1f %s" % (n, u) if u != "Б" else "%d Б" % n
        n /= 1024.0


def profile(path):
    """Профиль одной базы (только чтение)."""
    uri = "file:%s?mode=ro" % str(path).replace("\\", "/")
    info = {"path": str(path), "exists": path.exists(), "bytes": 0, "tables": [], "error": ""}
    if not path.exists():
        return info
    info["bytes"] = os.path.getsize(str(path))
    try:
        c = sqlite3.connect(uri, uri=True)
    except Exception as e:
        info["error"] = "connect: %s" % e
        return info
    try:
        try:
            names = [r[0] for r in c.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        except Exception as e:
            info["error"] = "master: %s" % e
            return info
        # Размер по таблицам через dbstat, если сборка sqlite его даёт; иначе — оценка
        # из page_count * page_size, распределённая по числу строк (грубо, но для приоритета
        # миграции «мозг vs свод» достаточно).
        sizes = {}
        try:
            for nm, sz in c.execute("SELECT name, SUM(pgsize) FROM dbstat GROUP BY name"):
                sizes[nm] = int(sz or 0)
        except Exception:
            sizes = {}
        if not sizes:
            try:
                page_b = c.execute("PRAGMA page_size").fetchone()[0]
                page_n = c.execute("PRAGMA page_count").fetchone()[0]
                total_b = int(page_b or 4096) * int(page_n or 0)
                rows_all = {}
                for nm in names:
                    try:
                        rows_all[nm] = c.execute('SELECT COUNT(*) FROM "%s"' % nm).fetchone()[0]
                    except Exception:
                        rows_all[nm] = 0
                s = sum(rows_all.values())
                for nm in names:
                    sizes[nm] = int(total_b * rows_all[nm] / s) if s else 0
            except Exception:
                sizes = {}
        for nm in names:
            try:
                rows = c.execute('SELECT COUNT(*) FROM "%s"' % nm).fetchone()[0]
            except Exception:
                rows = -1
            zone = "мозг" if nm in BRAIN else ("fts" if nm.startswith("fts") else "свод")
            info["tables"].append({"name": nm, "rows": rows,
                                   "bytes": sizes.get(nm, 0), "zone": zone})
        info["tables"].sort(key=lambda t: t["bytes"], reverse=True)
    finally:
        c.close()
    return info


def render(info):
    lines = ["=== ПРОФИЛЬ БАЗЫ: %s ===" % info["path"]]
    if not info["exists"]:
        lines.append("  базы нет на диске")
        return lines
    lines.append("  размер файла: %s, таблиц: %d" % (human(info["bytes"]), len(info["tables"])))
    if info["error"]:
        lines.append("  ВНИМАНИЕ: %s" % info["error"])
    brain_b = sum(t["bytes"] for t in info["tables"] if t["zone"] == "мозг")
    svod_b = sum(t["bytes"] for t in info["tables"] if t["zone"] == "свод")
    fts_b = sum(t["bytes"] for t in info["tables"] if t["zone"] == "fts")
    lines.append("  оценка по зонам: мозг %s · свод %s · fts %s"
                 % (human(brain_b), human(svod_b), human(fts_b)))
    for t in info["tables"]:
        lines.append("    %-22s строк %-8d %-9s [%s]"
                     % (t["name"], t["rows"], human(t["bytes"]) if t["bytes"] else "—", t["zone"]))
    return lines


def main(argv):
    as_json = "--json" in argv
    paths = [Path(a.strip('"')) for a in argv if not a.startswith("--")] or default_dbs()
    infos = [profile(p) for p in paths]
    live = [i for i in infos if i["exists"]]
    if as_json:
        print(json.dumps(infos, ensure_ascii=False, indent=1))
        return 0 if live else 2
    for info in infos:
        for ln in render(info):
            print(ln)
        print("")
    # Рекомендация по канону: если свод крупнее мозга — он кандидат в локальную db\.
    for info in infos:
        if not info["exists"]:
            continue
        brain_b = sum(t["bytes"] for t in info["tables"] if t["zone"] == "мозг")
        svod_b = sum(t["bytes"] for t in info["tables"] if t["zone"] == "свод")
        if svod_b > brain_b and svod_b > 0:
            print("РЕКОМЕНДАЦИЯ (канон): в %s свод (%s) крупнее мозга (%s) — по Волне 1 он должен"
                  % (info["path"], human(svod_b), human(brain_b)))
            print("  переехать в локальную db\\ инструмента, общая остаётся мозгом. Спока, режим ro.")
    return 0 if live else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
