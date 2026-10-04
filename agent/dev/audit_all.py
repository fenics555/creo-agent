# -*- coding: utf-8 -*-
"""audit_all.py — ПОЛНЫЙ АУДИТ ДОМА (слово владельца 03.10.2026).

ЧЕТЫРЕ ЧАСТИ, каждая с цифрами и живым выводом:
  1. ПРОГОН ИНСТРУМЕНТОВ — вызываются все инструменты вида read/check (без записи),
     собирается: отработал / упал, время, размер ответа, ПИШЕТ ЛИ ОН НА ДИСК и КУДА.
     Инструменты вида act НЕ ВЫЗЫВАЮТСЯ (они пишут) — они только сканируются по коду.
  2. КАРТА «ЧТО ДАЁТ И КУДА ПИШЕТ» — по исходнику блоков: пути log/reports/data.
  3. ВИДИТ ЛИ АГЕНТ ТО, ЧТО ПИШЕТ ИНСТРУМЕНТ — сверяем: файл/папка, которую инструмент
     объявляет как выход, существует ли.
  4. НАСТРОЙКИ — все ли объявлены, где хранятся, кто читает, что работает.

Запуск: cmd /c "python -X utf8 dev\\audit_all.py > data\\tmp\\audit.txt 2>&1"
Отчёт: D:\\AI\\log\\reports\\REPORT_audit_all_<дата>.md
"""
import io
import re
import sys
import time
from pathlib import Path

STDOUT = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace") if hasattr(sys.stdout, "buffer") else sys.stdout
sys.stdout = STDOUT
HERE = Path(__file__).resolve().parent
AGENT = HERE.parent
sys.path.insert(0, str(AGENT))

import tools_registry as TR          # noqa: E402
import settings as ST                # noqa: E402

LOG_DIR = Path(r"D:\AI\log")
REPORT_DIR = Path(r"D:\AI\log\reports")

# Куда пишут инструменты дома — регулярки по исходнику (живая карта, не выдумка).
WRITE_RX = [
    ("log", re.compile(r"D:\\\\AI\\\\log\\\\[A-Za-z0-9_\\\\.-]+|LOG_DIR\s*/\s*[\"'][A-Za-z0-9_]+|LOG_ROOT\s*/")),
    ("reports", re.compile(r"D:\\\\AI\\\\log\\\\reports|REPORT_DIR")),
    ("data", re.compile(r"data[\\\\/][A-Za-z0-9_.\\\\-]+|DATA_DIR")),
    ("backup", re.compile(r"backup")),
]


def src_of(block):
    """Исходник блока инструментов (по его имени)."""
    if not block:
        return ""
    p = AGENT / (block.replace(".", "/") + ".py")
    if p.is_file():
        try:
            return p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""
    cand = AGENT / block.split(".")[-1] / (block.split(".")[-1] + ".py")
    if cand.is_file():
        return cand.read_text(encoding="utf-8", errors="replace")
    return ""
# ТАЙМАУТ НА ИНСТРУМЕНТ (слово владельца «делай»). Живой факт 03.10.2026: прогон `--all`
# ЗАВИС на 70-й строке (следующий за `checks_list` инструмент ждал живое окружение —
# модель/CREOSON/сеть) и не дошёл до конца. Теперь каждый вызов ограничен по времени:
# не ответил за TOOL_TIMEOUT — помечается ЗАВИС, прогон идёт дальше. Поток демонский,
# поэтому итог всё равно печатается и процесс завершается.
TOOL_TIMEOUT = float(15)
_box = {}


def call_with_timeout(name, args, tmo=TOOL_TIMEOUT):
    """Возвращает ('ok', res) | ('err', тип, текст) | ('hang', секунд)."""
    import threading
    box = {}

    def worker():
        try:
            box["r"] = ("ok", TR.execute(name, args, client=None))
        except Exception as e:
            box["r"] = ("err", type(e).__name__, str(e)[:70])
    th = threading.Thread(target=worker, daemon=True)
    th.start()
    th.join(tmo)
    if th.is_alive():
        return ("hang", tmo)
    return box.get("r", ("hang", tmo))
# Но разрушительные (удаление, стирание, остановка) НЕ вызываются никогда: прогон не должен
# ничем жертвовать. Список составлен по ИМЕНИ — это осознанная граница, а не трусость.
DESTRUCTIVE_RX = re.compile(
    r"delete|erase|destroy|remove|purge|clean|wipe|kil+_|kill$|reset|drop|truncate|rename|write_|set_|apply|update|exec|run$|post|insert|backup|restore|archive|prune|migrate",
    re.I)
# Инструменты, которым БЕЗ аргументов нельзя: они требуют явного входа (и это правильно).
NEEDS_INPUT_RX = re.compile(r"^(?!.*\b(list|report|status|show|help|get|find|search|scan|audit|count)\b).*[a-z_]+$")


def main():
    out = []
    # Бэкап настроек перед прогоном пишущих инструментов — по закону 3 манифеста.
    try:
        import shutil
        import datetime
        _bk = AGENT / "data" / ("backup" /
                               ("pre_audit_all_%s_config.json" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S")))
        _bk.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(AGENT / "data" / "config.json", _bk)
        print("бекап настроек: %s" % _bk)
    except Exception as _be:
        print("бекап НЕ сделан: %s" % _be)
    full = "--all" in sys.argv

    def say(s=""):
        # ЖИВОЙ ДЕФЕКТ 03.10.2026: без flush вывод БУФЕРИЗУЕТСЯ, и при прогоне в файл
        # витрина выглядела «зависшей» на 70-й строке, хотя процесс работал (PID жив).
        # Прогон читают по ходу — значит сброс обязателен.
        print(s, flush=True)
        out.append(str(s))

    say("# ПОЛНЫЙ АУДИТ ДОМА · %s" % time.strftime("%Y-%m-%d %H:%M"))
    say("=" * 78)

    # ---------- 1-2. ПРОГОН И КАРТА ПИСАТЕЛЕЙ ----------
    say("## 1-2. ПРОГОН ИНСТРУМЕНТОВ + КАРТА «КУДА ПИШЕТ»")
    items = list(TR.iter_tools())
    say("инструментов в реестре: %d" % len(items))
    ran_ok = ran_fail = skipped = hung = 0
    writer_map = {}
    for kind, group, t in items:
        name = t.get("name")
        try:
            mo = TR.meta_of(name)
            block = mo[3] if mo else "?"
        except Exception:
            block = "?"
        src = src_of(block)
        where = [nm for nm, rx in WRITE_RX if src and rx.search(src)]
        if where:
            writer_map.setdefault(block, set()).update(where)
        if (t.get("kind") or "") not in ("read", "check"):
            if not full:
                skipped += 1
                continue
            if DESTRUCTIVE_RX.search(name or ""):
                say("  ПРОПУЩЕН (разрушительный) %-24s" % name)
                skipped += 1
                continue
            # пишущий инструмент вызывается с ПУСТЫМИ аргументами: так мы проверяем,
            # что он честно отказывает («нужен параметр»), а не пишет наугад.
            try:
                mo = TR.meta_of(name)
                block = mo[3] if mo else "?"
            except Exception:
                block = "?"
            src = src_of(block)
            where = [nm for nm, rx in WRITE_RX if src and rx.search(src)]
            t0 = time.time()
            try:
                r = call_with_timeout(name, {})
                if r[0] == "hang":
                    hung += 1
                    say("  ЗАВИС(вход) %-23s %6.1f с  (не ответил за %.0f с)"
                        % (name, time.time() - t0, TOOL_TIMEOUT))
                    continue
                if r[0] == "err":
                    ran_fail += 1
                    say("  ОТКАЗ(вход) %-25s %6.2f с  %s: %s"
                        % (name, time.time() - t0, r[1], r[2]))
                    continue
                ran_ok += 1
                say("  OK   %-30s %6.2f с  пишет:%-20s → %s"
                    % (name, time.time() - t0, ",".join(where) or "—",
                       str(r[1])[:50].replace("\n", " ")))
            except Exception as e:
                ran_fail += 1
                say("  ОТКАЗ %-28s %6.2f с  %s: %s"
                    % (name, time.time() - t0, type(e).__name__, str(e)[:60]))
            continue
        t0 = time.time()
        try:
            res = call_with_timeout(name, {})
            if res[0] == "hang":
                hung += 1
                say("  ЗАВИС %-32s %6.1f с  (не ответил за %.0f с)"
                    % (name, time.time() - t0, TOOL_TIMEOUT))
                continue
            if res[0] == "err":
                dt = time.time() - t0
                ran_fail += 1
                say("  ОТКАЗ %-28s %6.2f с  %s: %s" % (name, dt, res[1], res[2]))
                continue
            dt = time.time() - t0
            ran_ok += 1
            say("  OK   %-30s %6.2f с  %s" % (name, dt,
                                             ("пишет: " + ",".join(where)) if where else "—"))
        except Exception as e:
            dt = time.time() - t0
            ran_fail += 1
            say("  ОТКАЗ %-28s %6.2f с  %s: %s" % (name, dt, type(e).__name__, str(e)[:60]))
    say("  — успешно: %d, отказов: %d, зависло: %d, пропущено: %d"
        % (ran_ok, ran_fail, hung, skipped))
    say("  — блоки, которые пишут на диск:")
    for b, w in sorted(writer_map.items()):
        say("      %-30s → %s" % (b, ", ".join(sorted(w))))

    # ---------- 3. ВИДИТ ЛИ АГЕНТ ----------
    say("")
    say("## 3. ВИДИТ ЛИ АГЕНТ ТО, ЧТО ПИШЕТ ИНСТРУМЕНТ")
    say("   Правило дома: результат виден через (а) отчёт в log\\reports, (б) журнал")
    say("   log\\<инструмент>\\, (в) маршрут агента. Проверяем наличие папок и отчётов.")
    for d in ("reports", "checks", "win_check", "config_audit", "harvest", "navigator",
              "purge_versions", "plans", "skills"):
        p = LOG_DIR / d
        n = len(list(p.glob("*"))) if p.is_dir() else 0
        say("   %-16s %s" % (d, ("папка есть, объектов: %d" % n) if p.is_dir() else "НЕТ ПАПКИ"))
    reps = sorted(REPORT_DIR.glob("REPORT_*.md")) if REPORT_DIR.is_dir() else []
    say("   отчётов REPORT_*.md: %d, последний: %s"
        % (len(reps), reps[-1].name if reps else "—"))

    # ---------- 4. НАСТРОЙКИ ----------
    say("")
    say("## 4. НАСТРОЙКИ")
    cf = getattr(ST, "CONFIG_FILE", None)
    say("   файл настроек: %s (существует: %s)" % (cf, Path(cf).exists() if cf else "?"))
    d = ST._raw()
    say("   объявлено в REGISTRY: %d, в файле: %d" % (len(ST.REGISTRY), len(d)))
    bad = []
    for space, k, name, typ, defl, desc, ui in ST.REGISTRY:
        v = d.get(k, defl)
        prob = ""
        if k not in d:
            prob = "нет в файле (берётся умолчание)"
        elif typ == "int" and not isinstance(v, int):
            prob = "тип: ждали int, в файле %s" % type(v).__name__
        elif typ == "float" and not isinstance(v, (int, float)):
            prob = "тип: ждали float"
        elif typ == "bool" and not isinstance(v, bool):
            prob = "тип: ждали bool"
        elif typ == "list" and not isinstance(v, list):
            prob = "тип: ждали list"
        if prob:
            bad.append((k, prob))
    say("   расхождений по типу/наличию: %d" % len(bad))
    for k, p in bad[:20]:
        say("      %-24s %s" % (k, p))
    # Кто читает настройки. ДЕФЕКТ АУДИТА (03.10.2026, найден на себе): сканировались только
    # файлы в корне агента, поэтому настройки, которые читает ДВИЖОК В ПАПКЕ (log_days ->
    # log_clean\engine.py), ошибочно попадали в «никем не читается». Теперь обход рекурсивный
    # и без служебных папок.
    SKIP_DIRS = {"__pycache__", "data", "_legacy", "_disabled", "log"}
    readers = {}
    for py in AGENT.rglob("*.py"):
        rel = py.relative_to(AGENT)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if py.name == "settings.py" or py.name == "audit_all.py":
            continue
        try:
            s = py.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for space, k, *_ in ST.REGISTRY:
            if k in s:
                readers.setdefault(k, []).append(str(rel).replace("\\", "/"))
    say("   настроек, которые ЧИТАЕТ хотя бы один модуль: %d из %d" % (len(readers), len(ST.REGISTRY)))
    orphans = [k for space, k, *_ in ST.REGISTRY if k not in readers]
    say("   объявлено, но никем не читается: %d%s"
        % (len(orphans), (" — " + ", ".join(orphans[:12])) if orphans else ""))

    say("")
    say("=" * 78)
    say("ИТОГ: инструментов %d · прогнано %d · отказов %d · расхождений настроек %d"
        % (len(items), ran_ok, ran_fail, len(bad)))
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rf = REPORT_DIR / ("REPORT_audit_all_%s.md" % time.strftime("%Y-%m-%d_%H%M%S"))
    rf.write_text("\n".join(out), encoding="utf-8")
    print("отчёт: %s" % rf)
    return 0


if __name__ == "__main__":
    sys.exit(main())