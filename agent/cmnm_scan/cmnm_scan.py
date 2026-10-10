# -*- coding: utf-8 -*-
"""Разбор заголовков Creo-файлов: внутреннее имя модели (поле CMNM) против имени файла.
Если они расходятся — Creo не открывает модель по имени файла (XToolkitNotFound).
Только чтение, без Creo. Запуск: cmnm_scan.py <папка> [ещё папки...] [--limit N]
"""
import json
import os
import re
import sys
import time
from pathlib import Path

# Печать делаем кодировко-устойчивой: в cp1251 нет стрелки «→» (живая находка 23.09.2026).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
CREO = re.compile(r"\.(prt|asm|drw|frm|sec|lay)(\.\d+)?$", re.I)
REPORT_KEEP = int(os.environ.get("CMNM_REPORT_KEEP") or 20)   # сколько отчётов хранить


def _log_dir():
    """Папка отчётов. Закон канона №2: в КОДЕ нет абсолютного пути.
    Берём из настроек settings\\settings.json (ключ log_dir); если не задан или диск
    от него недоступен (перенос на другой ПК) — папка ВНУТРИ инструмента (переносимо).
    Меняется через settings:set / окно, путь проверяется при старте."""
    d = "log"
    sf = HERE / "settings" / "settings.json"
    try:
        if sf.exists():
            d = json.loads(sf.read_text(encoding="utf-8")).get("log_dir") or "log"
    except Exception:
        pass
    p = Path(d) if os.path.isabs(d) else (HERE / d)
    try:
        if not p.parent.exists():
            p = HERE / "log"
    except OSError:
        p = HERE / "log"
    return str(p)


LOG_DIR = _log_dir()


def write_report(lines):
    """Отчёт в файл: `run_<дата>_<время>.txt`. Секунды в имени — иначе два прогона в одну
    минуту затирают друг друга (найдено 02.10.2026). Старые отчёты ротируются, папка не растёт."""
    os.makedirs(LOG_DIR, exist_ok=True)
    logp = os.path.join(LOG_DIR, "run_%s.txt" % time.strftime("%Y-%m-%d_%H%M%S"))
    try:
        with open(logp, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception:
        return ""
    try:                                   # ротация: оставляем последние REPORT_KEEP
        olds = sorted((x for x in os.listdir(LOG_DIR)
                       if x.startswith("run_") and x.endswith(".txt")), reverse=True)
        for old in olds[REPORT_KEEP:]:
            os.remove(os.path.join(LOG_DIR, old))
    except Exception:
        pass
    return logp


def missing_roots(roots):
    """Папки, которых нет на диске: молчаливый «0 файлов» вводит в заблуждение (02.10.2026)."""
    return [r for r in roots if not os.path.isdir(r)]


def strip_len_prefix(nm):
    """Внутреннее имя в заголовке идёт с 3-значным HEX-префиксом длины:
    «007d25.asm» = 7 символов «d25.asm», «00bplatina.prt» = 11 «platina.prt».

    Живая находка 23.09.2026: без среза префикса программа показывала ЛОЖНОЕ расхождение
    на каждом файле (7 из 7 на пробной папке), потому что префикс считался частью имени.
    Срез делаем, если остаток по длине совпадает с префиксом.

    Живая находка 02.10.2026 (аудит): длина в префиксе — в БАЙТАХ UTF-8, а не в символах,
    и точка в имени не обязательна. Старое правило (символы + требование точки) давало
    131 ложное срабатывание на 490 файлах (27%): кириллические имена и имена без расширения.
    Правильное правило (байты UTF-8) даёт 86 — они настоящие (имя файла по коду, внутри по имени).
    """
    m = re.match(r"^([0-9a-fA-F]{3})(.+)$", nm)
    if m:
        rest = m.group(2)
        try:
            n_bytes = len(rest.encode("utf-8"))
        except Exception:
            n_bytes = len(rest)
        if abs(n_bytes - int(m.group(1), 16)) <= 1:
            return rest
    return nm


def header_name(path, raw=False):
    """Внутреннее имя модели из заголовка Creo (CMNM), либо None.
    raw=True — как записано в файле (с префиксом длины)."""
    try:
        with open(path, "rb") as f:
            raw_bytes = f.read(2048)
    except OSError:
        return None
    for enc in ("utf-8", "cp1251", "latin1"):
        try:
            head = raw_bytes.decode(enc, "ignore")
            m = re.search(r"^#-\s*CMNM\s+(.+)$", head, re.M)
            if m:
                nm = m.group(1).split("\\")[0].strip()   # в конце строки заголовка идёт «\» (перенос)
                if nm:
                    return nm if raw else strip_len_prefix(nm)
        except Exception:
            continue
    return None


def base_of(fn):
    return CREO.sub("", fn, count=1)


def scan(roots, limit=0, progress=None):
    """Обход и сверка внутреннего имени с именем файла. НИЧЕГО не печатает и не пишет —
    точка входа для окна программы.
    Возвращает: {'files': N, 'nofield': M, 'bad': [(полный путь, внутреннее имя, имя файла), ...],
                 'seconds': сек}
    Дефекты, найденные при переносе в окно (23.09.2026):
      * прежний `--limit` останавливал только внутренний цикл по файлам и продолжал обход папок;
      * стрелка «→» в отчёте роняла печать на cp1251-консоли (лечится `-X utf8`/reconfigure в main).
    """
    def say(s):
        if progress:
            progress(s)

    total = nofield = 0
    bad = []
    t0 = time.time()
    for root in roots:
        for dirpath, _dirnames, filenames in os.walk(root):
            for fn in filenames:
                if not CREO.search(fn):
                    continue
                full = os.path.join(dirpath, fn)
                total += 1
                nm = header_name(full)
                if nm is None:
                    nofield += 1
                    continue
                internal = base_of(nm.split("\\")[-1])
                filebase = base_of(fn)
                if internal.lower() != filebase.lower():
                    bad.append((full, nm, fn))
                    say("РАСХОЖДЕНИЕ: %s" % fn)
                if limit and total >= limit:
                    return {"files": total, "nofield": nofield, "bad": bad, "seconds": time.time() - t0}
    return {"files": total, "nofield": nofield, "bad": bad, "seconds": time.time() - t0}


def main(argv):
    roots, limit = [], 0
    i = 0
    while i < len(argv):
        if argv[i] == "--limit":
            i += 1
            limit = int(argv[i])
        else:
            roots.append(argv[i].replace('"', ""))
        i += 1
    if not roots:
        print(__doc__)
        return 2
    lines = ["=== ВНУТРЕННИЕ ИМЕНА (CMNM) против имён файлов ==="]
    for r in missing_roots(roots):
        lines.append("  ВНИМАНИЕ: папки нет на диске: %s" % r)
        print(lines[-1])
    res = scan(roots, limit)
    for full, nm, fn in res["bad"][:60]:
        lines.append("  РАСХОЖДЕНИЕ: файл «%s»  →  внутри «%s»" % (fn, nm))
        print(lines[-1])
    lines.append("\nфайлов просмотрено: %d; без поля CMNM: %d; расхождений: %d (%.0f с)"
                 % (res["files"], res["nofield"], len(res["bad"]), res["seconds"]))
    print(lines[-1])
    if len(res["bad"]) > 60:
        lines.append("…и ещё %d расхождений (полный список ниже)" % (len(res["bad"]) - 60))
        print(lines[-1])
        for full, nm, _fn in res["bad"][60:]:
            lines.append("  %s  →  %s" % (full, nm))
    logp = write_report(lines)
    if logp:
        print("отчёт: %s" % logp)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))