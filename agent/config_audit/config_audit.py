# -*- coding: utf-8 -*-
"""config_audit.py — аудит config.pro по фактам (класс Р, проверка без Creo).

Что делает: читает config.pro, вытаскивает КАЖДЫЙ путь (диск/UNC/$PRO_DIRECTORY/$PROSTD/
$CREO_COMMON_FILES) и проверяет его существование на диске. Отдельно проверяет,
жив ли `protkdat`, существует ли `search_path_file`, и есть ли `.lst` ограничений параметров.

Запуск:  python config_audit.py [путь\\к\\config.pro]
Вывод:   отчёт в stdout (строки ОК / НЕТ / подозрительно) + итог; код выхода 0 — всё на месте,
          1 — есть битые пути, 2 — файл конфига не найден или не читается.

ГДЕ ИЩЕТСЯ CREO (03.10.2026): поиск установки и рабочего config.pro живёт ОДИН раз на дом —
`agent\\agent\\creo_path.py` (приоритет: бат запуска → реестр → диск → настройки).
Здесь собственных копий поиска больше нет: раньше в коде и в настройках стоял путь
`D:\\PTC\\CREO12\\Creo 12.4.2.0` — на машине дом работает на CREO13, и при переезде домена
программа проверяла бы несуществующие пути и писала «ЕСТЬ БИТЫЕ ПУТИ».
"""
import os
import re
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_AGENT = os.path.dirname(_HERE)                                   # ...\\tools\\agent
for _p in (_AGENT,):                                   # общий модуль лежит в корне агента
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Волна 2: программа зовёт ЕДИНУЮ точку входа, а не ищет модуль сам.
# `creo_boot` сам добавит свои пути и честно переживёт отсутствие `creo_path`
# (грабля волны 1: перенос падал с ModuleNotFoundError).
import creo_boot as BOOT                                            # noqa: E402

# Журнал и отчёт программы (закон трёх рук, манифест п.19: одна база — один лог, один отчёт).
LOG_DIR = r"D:\AI\log\config_audit"
REPORT_DIR = r"D:\AI\log\reports"
REPORT_PREFIX = "REPORT_config_audit"
SETTINGS_FILE = os.path.normpath(os.path.join(_AGENT, "data", "config_audit_settings.json"))
# ЭТАП 9 (волна 10): карта плагинов дома. Читает audit_protk; живёт рядом с PROGRAM_REGISTRY.
PLUGINS_CARD = os.path.normpath(os.path.join(_AGENT, "dev", "PLUGINS.md"))
# АВТОНОМНОСТЬ (контракт 09_): при переносе программы в изоляцию папки `dev` рядом нет.
# Живой провал 03.10.2026 (vol2): копия движка в изоляции не нашла карту и пометила КАЖДЫЙ
# protkdat как «нет_в_карте» → RC 1. Поэтому ищем карту по трём местам, и если её нет —
# это «нет данных», а не провал: проверка просто не сверяет.
PLUGINS_CARD_ALT = os.path.normpath(os.path.join(_HERE, "PLUGINS.md"))


def find_plugins_card():
    """Где карта плагинов: рядом с движком → в настройках → в `dev\\` агента."""
    st = ""
    try:
        import json
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            st = (json.load(f).get("plugins_card") or "")
    except Exception:
        st = ""
    for cand in (st, PLUGINS_CARD_ALT, PLUGINS_CARD):
        if cand and os.path.isfile(cand):
            return cand
    return ""
# Путь к config.pro по умолчанию — через общий поиск (рядом с батом запуска).
CONFIG = sys.argv[1] if len(sys.argv) > 1 else (BOOT.config_path() or "")
# $PROSTD не зависит от версии Creo: это папка настроек дома.
VAR_DEFAULT = {"$PROSTD": r"Z:\PTC\CREO-START\НАСТРОЙКИ"}


# 03.10.2026: собственные копии поиска удалены. Их работу делает общий `creo_path.find()`:
# бат запуска -> реестр -> диск. Вторая копия поиска = расхождение версий через месяц.


def load_vars():
    """Подстановки переменных Creo. 03.10.2026 — ЕДИНЫЙ источник, общий поиск дома:
    1) `agent\\agent\\creo_path.find()` — бат запуска → реестр → диск → настройки;
    2) блок `creo_vars` в настройках программы (только для $PROSTD и прочего нестандартного).

    Пути к установке НЕ зашиты: на машине стоят CREO12 и CREO13, дом работает на CREO13.
    """
    import json
    out = dict(VAR_DEFAULT)
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            st = json.load(f)
        for k, v in (st.get("creo_vars") or {}).items():
            # Пути установки из настроек НЕ принимаются: они устаревают при переезде
            # домена. Из настроек берём только то, что не является путём к Creo.
            if k.startswith("$") and v and k not in ("$PRO_DIRECTORY", "$CREO_COMMON_FILES"):
                out[k] = v
    except Exception:
        pass
    com, par, why = BOOT.find()
    if par:
        out["$PRO_DIRECTORY"] = par
    if com:
        out["$CREO_COMMON_FILES"] = com
    return out


def find_install():
    """(parametric, common_files, откуда) — для окна и отчёта, чтобы было видно,
    ПРОТИВ какого Creo шла проверка (при переезде домена это главный вопрос)."""
    com, par, why = BOOT.find()
    return par, com, why
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


def audit_protk(config_path):
    """ЭТАП 9 (волна 10): плагины боя против карты `dev\\PLUGINS.md`.

    ЗАЧЕМ (профилактика из плана): новый `protkdat`, поставленный в боевой `config.pro`,
    обязан попасть в карту плагинов. Раньше про него узнавали случайно, через поломку.

    ЧТО ЧИТАЕТ:
      1) все строки `protkdat` из config.pro, включая закомментированные (`!`) — они
         показываются как выключенные, но тоже должны быть зафиксированы;
      2) раздел «ЖИВАЯ ПРОВЕРКА» карты: строки вида `- protkdat <путь>`.

    ЧТО ВОЗВРАЩАЕТ: {'in_config': N, 'in_card': M, 'active': K, 'problems': [...]}
      problems — расхождения: 'нет_в_карте' (плагин в бою не зафиксирован — ЭТО ПРОВАЛ),
      'нет_на_диске' (файл protk.dat отсутствует — провал для активных строк),
      'нет_в_бою' (карта обещает плагин, которого в config.pro нет — предупреждение,
      обычно значит «модуль сняли», это НЕ ошибка дома).

    Только чтение: ни config.pro, ни PLUGINS.md, ни protk.dat программа не меняет.
    """
    card = find_plugins_card()
    known = {}
    card_found = bool(card)
    if card_found:
        with open(card, encoding="utf-8") as f:
            for n, raw in enumerate(f, 1):
                t = raw.strip()
                if not t.startswith("- protkdat"):
                    continue
                path = norm(t.split("- protkdat", 1)[1].strip())
                if path:
                    known[path.lower()] = {"line": n, "path": path}
    rows, problems = [], []
    n_cfg = 0
    if not os.path.isfile(config_path):
        raise FileNotFoundError("нет файла config.pro: %s" % config_path)
    with open(config_path, encoding="utf-8-sig", errors="replace") as f:
        for n, raw in enumerate(f, 1):
            line = raw.strip()
            off = line.startswith("!")
            if off:
                # Живой дефект 03.10.2026: `!` снимался только у НЕзакомментированных строк,
                # из-за чего выключенные плагины (KeyShot, строка 377) вообще не попадали
                # в разбор — программа рапортовала «нет_в_бою» для зафиксированного модуля.
                line = line.lstrip("!").strip()
            if not line.lower().startswith("protkdat"):
                continue
            val = line.split(None, 1)[1].strip() if len(line.split(None, 1)) == 2 else ""
            if not val:
                continue
            n_cfg += 1
            path = norm(val)
            rec = {"line": n, "raw": val, "path": path, "active": not off,
                   "on_disk": os.path.isfile(path),
                   "in_card": path.lower() in known if card_found else None}
            rows.append(rec)
            if not card_found:
                # Карты нет (перенос в изоляцию, папки dev рядом нет) — это «нет данных»,
                # а не провал: молча не сверяем, но CLI об этом говорит честно.
                continue
            if not rec["in_card"]:
                problems.append({"kind": "нет_в_карте", "line": n, "path": path, "active": not off})
            elif not off and not rec["on_disk"]:
                problems.append({"kind": "нет_на_диске", "line": n, "path": path, "active": True})
    for key, rec in known.items():
        if not any(r["path"].lower() == key for r in rows):
            problems.append({"kind": "нет_в_бою", "line": rec["line"],
                             "path": rec["path"], "active": False})
    hard = sum(1 for p in problems if p["kind"] in ("нет_в_карте", "нет_на_диске"))
    return {"in_config": n_cfg, "in_card": len(known), "active": sum(1 for r in rows if r["active"]),
            "problems": problems, "hard": hard, "rows": rows, "card": card,
            "card_found": card_found}


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
    if not CONFIG:
        print("НЕЧЕГО ПРОВЕРЯТЬ: рабочий config.pro не найден")
        print("укажи его вручную:  config_audit.bat \"<путь>\\config.pro\"")
        return 2
    print("АУДИТ CONFIG.PRO: %s" % CONFIG)
    print("=" * 78)
    par, com, why = find_install()
    print("проверка ПРОТИВ: %s (%s)" % (par or "установка не найдена", why))
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
    # --- ЭТАП 9 (волна 10): плагины боя против карты PLUGINS.md ---------------------
    protk = None
    try:
        protk = audit_protk(CONFIG)
        print("ПЛАГИНЫ (protkdat): в config.pro %d, в карте %d, активных %d"
              % (protk["in_config"], protk["in_card"], protk["active"]))
        if not protk.get("card_found"):
            # Честно: карты нет — сверять не с чем. Это «нет данных», НЕ провал,
            # иначе перенос программы в изоляцию всегда давал бы RC 1.
            print("   карта плагинов не найдена — сверка с картой пропущена (нет данных)")
        else:
            print("   карта: %s" % protk["card"])
        for r in protk["rows"]:
            print("   строка %-4d %-9s %-7s %s"
                  % (r["line"], "активен" if r["active"] else "ВЫКЛЮЧЕН",
                     "есть" if r["on_disk"] else "НЕТ", r["path"]))
        for pr in protk["problems"]:
            print("   РАСХОЖДЕНИЕ [%s] строка %d: %s" % (pr["kind"], pr["line"], pr["path"]))
        if not protk["problems"] and protk.get("card_found"):
            print("   плагины боя совпадают с картой, файлы на месте")
    except Exception as e:
        print("ПЛАГИНЫ: не разобрал (%s: %s) — на вердикт по путям не влияет"
              % (type(e).__name__, e))
    print("=" * 78)
    write_report(res, CONFIG, secs)
    if res["missing"]:
        print("ЧТО ДЕЛАТЬ: файла нет -> или положить файл(ы) по этому пути, или закомментировать")
        print("настройку (`!`), и записать причину рядом — как сделано с template_* 23.09.2026.")
        return 1
    if protk is not None and protk["hard"]:
        print("все пути на месте, но ПЛАГИНЫ: расхождений %d (см. PLUGINS.md)."
              % protk["hard"])
        return 1
    print("все пути на месте, плагины зафиксированы.")
    return 0


if __name__ == "__main__":
    sys.exit(main())