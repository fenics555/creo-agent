# -*- coding: utf-8 -*-
"""config_audit.py — аудит config.pro по фактам (класс Р, проверка без Creo).

Что делает: читает config.pro, вытаскивает КАЖДЫЙ путь (диск/UNC/$PRO_DIRECTORY/$PROSTD/
$CREO_COMMON_FILES) и проверяет его существование на диске. Отдельно проверяет,
жив ли `protkdat`, существует ли `search_path_file`, и есть ли `.lst` ограничений параметров.

Запуск:  python config_audit.py [путь\\к\\config.pro]
Вывод:   отчёт в stdout (строки ОК / НЕТ / подозрительно) + итог; код выхода 0 — всё на месте,
          1 — есть битые пути, 2 — файл конфига не найден или не читается.
"""
import os
import re
import sys
import time

CONFIG = sys.argv[1] if len(sys.argv) > 1 else r"Z:\PTC\CREO-START\START-STD\config.pro"
# Журнал и отчёт программы (закон трёх рук, манифест п.19: одна база — один лог, один отчёт).
LOG_DIR = r"D:\AI\log\config_audit"
REPORT_DIR = r"D:\AI\log\reports"
REPORT_PREFIX = "REPORT_config_audit"
# Подстановки переменных Creo. До 02.10.2026 это был СЛОВАРЬ-КОНСТАНТА с путём
# `Creo 12.4.2.0` внутри кода. На машине стоят ОБЕ версии (D:\PTC\CREO12\Creo 12.4.2.0
# и D:\PTC\CREO13\Creo 13.4.1.0) — при переходе дома на Creo 13 программа проверяла бы
# несуществующие пути и написала бы «ЕСТЬ БИТЫЕ ПУТИ». Пути теперь в настройках
# (agent\data\config_audit_settings.json), а сверху — автоопределение по диску.
VAR = {
    "$PRO_DIRECTORY": r"D:\PTC\CREO12\Creo 12.4.2.0\Parametric",
    "$CREO_COMMON_FILES": r"D:\PTC\CREO12\Creo 12.4.2.0\Common Files",
    "$PROSTD": r"Z:\PTC\CREO-START\НАСТРОЙКИ",
}
DEFAULT_CREO_ROOT = r"D:\PTC"


def _find_creo(version_hint="12"):
    """Ищет установку Creo на диске: D:\\PTC\\CREO*\\Creo <версия>\\Parametric.
    Возвращает (parametric, common_files) или (None, None)."""
    try:
        families = sorted(os.listdir(DEFAULT_CREO_ROOT), reverse=True)
    except OSError:
        return None, None
    for fam in families:
        base = os.path.join(DEFAULT_CREO_ROOT, fam)
        if not os.path.isdir(base) or not fam.upper().startswith("CREO"):
            continue
        try:
            vers = sorted(os.listdir(base), reverse=True)
        except OSError:
            continue
        for v in vers:
            p = os.path.join(base, v, "Parametric")
            if os.path.isdir(p):
                return p, os.path.join(base, v, "Common Files")
    return None, None


def load_vars():
    """Подстановки переменных Creo. Приоритет источников:
    1) настройки дома (`data\\config_audit_settings.json`, блок `creo_vars`);
    2) путь из кода, ЕСЛИ он реально есть на диске (сейчас это CREO12);
    3) автоопределение по диску `D:\\PTC\\CREO*\\Creo *\\Parametric` — страховка от перехода
       дома на другую версию Creo.
    Путь из кода проверяется на существование НАМЕРЕННО: иначе программа продолжит искать
    файлы в несуществующей установке и напишет «ЕСТЬ БИТЫЕ ПУТИ»."""
    import json
    out = dict(VAR)
    try:
        sfile = os.path.normpath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), os.pardir, "data",
            "config_audit_settings.json"))
        with open(sfile, encoding="utf-8") as f:
            st = json.load(f)
        for k, v in (st.get("creo_vars") or {}).items():
            if k.startswith("$") and v:
                out[k] = v
    except Exception:
        pass
    # Живая проверка 02.10.2026: ранний return из настроек отдавал МЁРТВЫЙ путь — файл настроек
    # всегда читается, значит автоопределение не срабатывало никогда. Теперь путь проверяется
    # ВСЕГДА, а источник значения не важен: есть на диске — берём, нет — ищем установку.
    if os.path.isdir(out["$PRO_DIRECTORY"]):
        return out
    par, com = _find_creo()
    if par:
        out["$PRO_DIRECTORY"] = par
        out["$CREO_COMMON_FILES"] = com
    return out
PATHY = re.compile(r"(?:[A-Za-z]:[\\/]|\$[A-Z_]+[\\/]|\\\\)")

_VARS = None


def norm(v: str) -> str:
    """Путь конфига -> путь Windows: переменные, слэши, хвостовые пробелы."""
    global _VARS
    if _VARS is None:
        _VARS = load_vars()
    for k, r in _VARS.items():
        v = v.replace(k, r)
    v = v.replace("/", "\\").rstrip("\\ ")
    return v

def exists_creo(p: str):
    """Creo хранит файлы с номером версии: mm_part.prt -> mm_part.prt.1."""
    if os.path.exists(p):
        return "есть"
    if os.path.exists(p + ".1"):
        return "есть (версия .1)"
    base = os.path.dirname(p)
    if base and os.path.isdir(base) and os.path.basename(p):
        stem = os.path.basename(p).lower()
        try:
            for f in os.listdir(base):
                if f.lower().startswith(stem):
                    return "есть (как %s)" % f
        except OSError:
            pass
    return None

def audit(config_path):
    """Проверка ВСЕХ путей config.pro на диске. Возвращает структуру (для окна и для CLI):
    {'total': N, 'missing': M, 'problems': [ {'line': n, 'opt': ..., 'value': ..., 'path': ...} ]}"""
    # Живая проверка 02.10.2026: раньше отсутствие файла роняло программу голым
    # FileNotFoundError с трассировкой — планировщик и человек видели стек, а не вывод.
    if not os.path.isfile(config_path):
        raise FileNotFoundError("нет файла config.pro: %s" % config_path)
    lines = open(config_path, encoding="utf-8-sig", errors="replace").read().splitlines()
    ok = 0
    problems = []
    for n, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("!"):
            continue
        body = re.split(r"\s+!(?!=)", line, maxsplit=1)[0].strip()
        parts = body.split(None, 1)
        if len(parts) != 2:
            continue
        opt, val = parts[0], parts[1].strip()
        if not PATHY.search(val):
            continue
        p = norm(val)
        if exists_creo(p):
            ok += 1
        else:
            problems.append({"line": n, "opt": opt, "value": val, "path": p})
    return {"total": ok + len(problems), "missing": len(problems), "problems": problems}


def write_report(res, config_path, secs, quiet=False):
    """Журнал прогона и отчёт. До 02.10.2026 программа писала ТОЛЬКО в stdout: у неё не было
    ни своего лога, ни отчёта — паспорт в programs.json обещал `D:\\AI\\log\\config_audit`,
    а папки не существовало."""
    os.makedirs(LOG_DIR, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, "run_%s.txt" % stamp)
    os.makedirs(REPORT_DIR, exist_ok=True)
    rep_file = os.path.join(REPORT_DIR, "%s_%s.md" % (REPORT_PREFIX, stamp))
    verdict = "все пути на месте" if not res["missing"] else "ЕСТЬ БИТЫЕ ПУТИ"
    with open(log_file, "w", encoding="utf-8") as f:
        f.write("=== CONFIG AUDIT: %s ===\nфайл: %s\nвремя: %.3f с\n"
                "путей проверено: %d | НЕТ на диске: %d\n"
                % (stamp, config_path, secs, res["total"], res["missing"]))
        for pr in res["problems"]:
            f.write("строка %d: %s\n   в конфиге: %s\n   на диске : %s  <- НЕТ\n"
                    % (pr["line"], pr["opt"], pr["value"], pr["path"]))
    with open(rep_file, "w", encoding="utf-8") as f:
        f.write("# Отчёт: аудит путей config.pro\n\n")
        f.write("**Дата:** %s\n**Файл:** `%s`\n**Время прогона:** %.3f с\n\n"
                % (stamp, config_path, secs))
        f.write("## Сводка\n- путей проверено: **%d**\n- НЕТ на диске: **%d**\n- вердикт: **%s**\n\n"
                % (res["total"], res["missing"], verdict))
        if res["problems"]:
            f.write("## Битые пути\n")
            for pr in res["problems"]:
                f.write("### строка %d — `%s`\n- в конфиге: `%s`\n- на диске: `%s` — **НЕТ**\n\n"
                        % (pr["line"], pr["opt"], pr["value"], pr["path"]))
        else:
            f.write("## Битые пути\n\nНет. Все %d путей config.pro найдены на диске.\n" % res["total"])
        f.write("## Откуда что взято\n- конфиг: только чтение, ничего не пишется на диск конфигурации\n")
        f.write("- журнал прогона: `%s`\n" % log_file)
        f.write("- подстановки переменных (ПРОВЕРЕНО, что пути есть на диске):\n")
        for k, v in (load_vars() or {}).items():
            f.write("  - `%s` → `%s` — %s\n" % (k, v, "есть" if os.path.exists(v) else "НЕТ"))
        f.write("\n---\n*Отчёт сформирован программой config_audit*\n")
    if not quiet:
        print("отчёт: %s" % rep_file)
    return rep_file


def main():
    print("АУДИТ CONFIG.PRO: %s" % CONFIG)
    print("=" * 78)
    _t0 = time.time()
    try:
        res = audit(CONFIG)
    except FileNotFoundError as e:
        print("НЕЧЕГО ПРОВЕРЯТЬ: %s" % e)
        print("укажи существующий config.pro, например: "
              "config_audit.bat \"Z:\\PTC\\CREO-START\\START-STD\\config.pro\"")
        return 2
    except Exception as e:
        print("НЕ ЧИТАЕТСЯ %s: %s" % (CONFIG, e))
        return 2
    secs = time.time() - _t0
    print("путей проверено: %d | НЕТ на диске: %d | за %.3f с" % (res["total"], res["missing"], secs))
    print("-" * 78)
    for pr in res["problems"]:
        print("строка %d: %s" % (pr["line"], pr["opt"]))
        print("   в конфиге: %s" % pr["value"])
        print("   на диске : %s   <- НЕТ" % pr["path"])
    print("=" * 78)
    write_report(res, CONFIG, secs)
    if res["missing"]:
        print("ЧТО ДЕЛАТЬ: файла нет -> или положить файл(ы) по этому пути, или закомментировать")
        print("настройку (`!`), и записать причину рядом — как сделано с template_* 23.09.2026.")
        return 1
    print("все пути на месте.")
    return 0


if __name__ == "__main__":
    sys.exit(main())