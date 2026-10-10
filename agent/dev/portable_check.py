# -*- coding: utf-8 -*-
"""portable_check.py — автопроверка переносимости инструмента дома (Волна 0.2 плана).

Копирует папку инструмента в свою урну, чистит __pycache__/*.pyc, гоняет движок из КОПИИ,
проверяет: не импортирует ли код агента, нет ли зашитых абсолютных путей, корректен ли код
возврата. Печатает вердикт ПЕРЕНОСИТ / НЕ ПЕРЕНОСИТ (с причиной).

Запуск:  python dev\\portable_check.py <папка инструмента> [--keep]
Пример:  python dev\\portable_check.py tools\\agent\\cmnm_scan
Вердикт в коде возврата: 0 — переносит, 1 — не переносит.
Ничего в доме не правит: копия живёт в урне и удаляется в конце (кроме --keep).
"""
import io
import os
import re
import shutil
import subprocess
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DEV = os.path.dirname(os.path.abspath(__file__))
AGENT = os.path.dirname(DEV)                       # tools\\agent
URN = os.path.join(os.path.dirname(AGENT), "..", "log", "urn", "portable")  # D:\\AI\\log\\urn\\portable
URN = os.path.abspath(URN)

# Импорты, запрещающие жизнь без агента (инструмент должен быть самостоятелен).
AGENT_IMPORTS = re.compile(
    r"^\s*(import|from)\s+(core|loop|tools_registry|settings|agent|spec_tools|diagnostic_tools)\b",
    re.M)
# Абсолютные пути Windows в коде — ломают перенос (закон канона №2).
ABS_PATH = re.compile(r"[A-Za-z]:\\\\")


def say(s=""):
    print(s)


def read_json(path):
    import json
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def clean_pyc(root):
    """Убираем __pycache__ и *.pyc — при копировании они попадают и мешают чистому прогону."""
    removed = 0
    for dp, dns, fns in os.walk(root):
        for d in list(dns):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(dp, d), ignore_errors=True)
                dns.remove(d)
                removed += 1
        for f in fns:
            if f.endswith(".pyc"):
                try:
                    os.remove(os.path.join(dp, f))
                    removed += 1
                except OSError:
                    pass
    return removed


def find_engine(tool_dir, manifest):
    """Движок: из манифеста 'engine', иначе <имя папки>.py."""
    if isinstance(manifest, dict) and manifest.get("engine"):
        cand = os.path.join(tool_dir, manifest["engine"])
        if os.path.isfile(cand):
            return cand
    name = os.path.basename(tool_dir.rstrip("\\/"))
    cand = os.path.join(tool_dir, name + ".py")
    return cand if os.path.isfile(cand) else ""


def py_files(tool_dir):
    out = []
    for dp, dns, fns in os.walk(tool_dir):
        dns[:] = [d for d in dns if d not in ("__pycache__", "backup_settings", "backup")]
        for f in fns:
            if f.endswith(".py"):
                out.append(os.path.join(dp, f))
    return out


def run(cmd, cwd):
    """Прогон из копии. Возвращает (rc, хвост вывода). Таймаут 25 с — шаг ноги не должен висеть."""
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           timeout=25, encoding="utf-8", errors="replace")
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "ТАЙМАУТ 25 с"
    except Exception as e:
        return 125, "%s: %s" % (type(e).__name__, e)


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    keep = "--keep" in argv
    if not args:
        say(__doc__)
        return 2
    src = os.path.abspath(args[0].strip('"'))
    if not os.path.isdir(src):
        say("НЕТ ПАПКИ: %s" % src)
        return 2
    name = os.path.basename(src.rstrip("\\/"))
    say("=== ПРОВЕРКА ПЕРЕНОСИМОСТИ: %s ===" % name)
    say("источник: %s" % src)

    fails, warns = [], []

    # 1. Манифест и паспорт (канон §3)
    man_path = os.path.join(src, "tool.json")
    manifest = {}
    if os.path.isfile(man_path):
        try:
            manifest = read_json(man_path)
            say("[ok] tool.json прочитан (id=%s)" % manifest.get("id", "?"))
        except Exception as e:
            fails.append("tool.json битый: %s" % e)
    else:
        warns.append("нет tool.json — манифест контракта отсутствует")
    if not os.path.isfile(os.path.join(src, "README.md")):
        warns.append("нет README.md")

    engine = find_engine(src, manifest)
    if not engine:
        say("НЕ НАЙДЕН ДВИЖОК — проверять нечего")
        return 1
    say("[ok] движок: %s" % os.path.basename(engine))

    # 2. Исходники не должны импортировать агента (закон переносимости)
    agent_hits = []
    for py in py_files(src):
        try:
            txt = open(py, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        if AGENT_IMPORTS.search(txt):
            agent_hits.append(os.path.basename(py))
        for m in ABS_PATH.finditer(txt):
            line = txt[:m.start()].count("\n") + 1
            warns.append("абс. путь %s в %s:%d" % (m.group(0), os.path.basename(py), line))
    if agent_hits:
        fails.append("импорт кода агента: %s" % ", ".join(sorted(set(agent_hits))))
    else:
        say("[ok] код агента не импортируется")

    # 3. Живой прогон ИЗ КОПИИ в чистом месте (урна)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    dst = os.path.join(URN, "%s_%s" % (name, stamp))
    os.makedirs(URN, exist_ok=True)
    if os.path.exists(dst):
        shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)
    removed = clean_pyc(dst)
    say("[ok] копия в урну: %s (убрано pyc: %d)" % (dst, removed))
    eng_copy = os.path.join(dst, os.path.basename(engine))
    py = sys.executable or "python"

    # 3a. Движок отвечает на --help / --version (не падает импортом)
    rc_h, out_h = run([py, "-X", "utf8", os.path.basename(engine), "--help"], dst)
    if rc_h in (0, 1, 2):
        say("[ok] движок запускается из копии (--help rc=%d)" % rc_h)
    elif rc_h == 124:
        warns.append("движок --help повис (25 с) — возможно, ждёт ввода")
    else:
        fails.append("движок --help упал rc=%d: %s" % (rc_h, out_h.strip()[-200:]))

    # 3b. Прогон на НЕСУЩЕСТВУЮЩЕМ пути → обязан быть внятный RC 2, не падение
    rc_m, out_m = run([py, "-X", "utf8", os.path.basename(engine),
                       os.path.join(dst, "нет_такой_папки_%%")], dst)
    crashed = "Traceback" in out_m or rc_m not in (0, 1, 2)
    if crashed:
        fails.append("на недоступном пути упал (rc=%d): %s" % (rc_m, out_m.strip()[-200:]))
    else:
        say("[ok] недоступный путь → внятный отказ rc=%d (не падение)" % rc_m)

    # 3c. Прогон на настоящей маленькой выборке (движок scan на самой папке инструмента)
    rc_s, out_s = run([py, "-X", "utf8", os.path.basename(engine), dst], dst)
    say("[info] прогон на копии rc=%d: %s" % (rc_s, out_s.strip().splitlines()[-1] if out_s.strip() else "(пусто)"))
    if "Traceback" in out_s:
        fails.append("Traceback при рабочем прогоне: %s" % out_s.strip()[-200:])
    if rc_s not in (0, 1, 2, 124):
        fails.append("рабочий прогон вернул rc=%d (вне 0/1/2)" % rc_s)

    # 4. Уборка копии (если не попросили оставить)
    if not keep:
        shutil.rmtree(dst, ignore_errors=True)
        say("[ok] копия удалена")
    else:
        say("[info] копия оставлена: %s" % dst)

    # ИТОГ
    say("")
    for w in warns:
        say("ПРЕДУПРЕЖДЕНИЕ: %s" % w)
    for f in fails:
        say("ДЕФЕКТ: %s" % f)
    if fails:
        say("ВЕРДИКТ: НЕ ПЕРЕНОСИТ (%d дефект., %d предупр.)" % (len(fails), len(warns)))
        return 1
    say("ВЕРДИКТ: ПЕРЕНОСИТ (%d предупр.)" % len(warns))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

