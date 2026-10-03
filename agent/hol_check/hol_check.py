# -*- coding: utf-8 -*-
r"""hol_check.py — ПРОВЕРКА ТАБЛИЦ ОТВЕРСТИЙ (класс Р, только чтение).

Зачем: 18.09.2026 Creo писал в каждом трейле
`hole_charts_thread_series — ошибка чтения диаграммы отверстий при старте`.
Причина найдена вживую: в файле `GOST_DK.hol` шапка THREAD_DATA содержала
РАЗОРВАННОЕ имя `TAPER_AN` + `GLE WASHOUT_ANGLE`. Файл починили 24.09.2026 — ошибка ушла.
Эта программа ловит такое ДО старта Creo и ничего не чинит (класс Р).

Запуск: hol_check.bat [папка]     RC 0 — ошибок нет · 1 — есть ошибки · 2 — нечего проверять
"""
import csv
import glob
import io
import os
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_AGENT = _HERE.parent
for _p in (_AGENT,):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

LOG_DIR = Path(r"D:\AI\log\hol_check")
REPORT_DIR = Path(r"D:\AI\log\reports")

# Боевые папки: основная и СТАРОЕ (план, этап 1: обход ГОСТ/DIN/source/СТАРОЕ)
HOLE_ROOT = Path(r"Z:\PTC\CREO-START\НАСТРОЙКИ\ТАБЛИЦА_ОТВЕРСТИЙ")
DEFAULT_DIRS = [HOLE_ROOT, HOLE_ROOT / "СТАРОЕ"]
ETALON = HOLE_ROOT / "g6111_konich_60.hol"

# Имена колонок эталона (основа проверки «разорвано ли имя»).
KNOWN_COLS = [
    "FASTENER_ID", "BASIC_DIAM", "PIPE_OD", "THREAD", "PITCH", "TAP_DR", "TAP_DEC",
    "PERCENT_THREAD", "CLEAR_DR_CLOSE", "CLOSE_DEC", "CLEAR_DR_FREE", "FREE_DEC",
    "CLEAR_DR_MED", "MED_DEC", "CBOREDIAM", "CBOREDEPTH", "CSINKDIAM", "CSINKANGLE",
    "BOTCSINKDIAM", "BOTCSINKANGLE", "THREAD_LENGTH", "HANDTIGHT_LENGTH", "WRENCHING_LENGTH",
    "DEF_HOLE_DEPTH", "MAJOR_DIAM_START", "PITCH_DIAM_START", "MINOR_DIAM_START",
    "MAJOR_DIAM_END", "PITCH_DIAM_END", "MINOR_DIAM_END", "THREAD_HEIGHT", "THREAD_ANGLE",
    "TAPER_ANGLE", "WASHOUT_ANGLE",
]
KNOWN = set(KNOWN_COLS)
ICON = {"error": "FAIL", "warn": "WARN", "ok": "OK"}


def read_text(path):
    """Читает .hol в ANSI/CP1251 (в файлах есть кириллица). Возвращает (текст, код|ошибка)."""
    for enc in ("cp1251", "latin-1"):
        try:
            return Path(path).read_text(encoding=enc), enc
        except UnicodeDecodeError:
            continue
        except Exception as e:
            return None, "не читается: %s" % e
    return None, "не декодируется ни в cp1251, ни в latin-1"


def split_cols(line):
    """Колонки строки .hol.

    ЖИВОЙ ФАКТ (проверено на боевых файлах 03.10.2026): разделитель бывает двух видов —
    табуляция (`GOST_DK.hol`) ИЛИ два и более пробела (`ISO.hol`, `g12876_screw.hol`,
    выравнивание «на глаз»). Поэтому сначала режем по табам, а если табов нет —
    по 2+ пробелам. Второй элемент — какой разделитель реально найден.
    """
    raw = line.rstrip("\r\n")
    if "\t" in raw:
        return [c for c in raw.split("\t") if c.strip() != ""], "TAB"
    import re
    return [c for c in re.split(r"\s{2,}", raw.strip()) if c.strip() != ""], "2+ ПРОБЕЛА"


def find_sections(lines):
    """Номера строк (с 0) секций TABLE_DATA и THREAD_DATA."""
    out = {}
    for i, l in enumerate(lines):
        s = l.strip()
        if s in ("TABLE_DATA", "THREAD_DATA") and s not in out:
            out[s] = i
    return out


def broken_names(head):
    """РАЗОРВАННЫЕ ИМЕНА: кусок известного имени, склеенный с соседним.

    Именно так выглядел боевой дефект: `TAPER_AN` + `GLE WASHOUT_ANGLE`.
    Возвращает список объяснений вида 'TAPER_AN → TAPER_A + N'."""
    out = []
    for c in head:
        cs = c.strip()
        if cs in KNOWN or not cs:
            continue
        words = cs.split()
        # 1) склейка двух имён без пробела: TAPER_ANGLE -> TAPER_AN|GLE
        for full in KNOWN:
            for cut in range(3, len(full) - 2):
                if not cs.startswith(full[:cut]):
                    continue
                rest = cs[cut:]
                if not rest:                 # остаток пустой — это не разрыв, а ошибка проверки
                    continue
                for other in KNOWN:
                    if other != full and (other.startswith(rest) or rest == other):
                        out.append("%s → %s + %s" % (cs, full[:cut], rest))
                        break
                if out and out[-1].startswith(cs + " "):
                    break
            if out and out[-1].startswith(cs + " "):
                break
        # 2) два слова, где ПЕРВОЕ слово само по себе не является колонкой эталона,
        #    а второе — кусок известного: "GLE WASHOUT_ANGLE".
        #    Если первое слово — полное известное имя (PIPE_OD THREAD), это НЕ разрыв:
        #    это просто две колонки, склеенные разделителем (живой факт, эталон).
        if len(words) > 1 and not out:
            head_w, tail = words[0], words[-1]
            if head_w not in KNOWN:
                for full in KNOWN:
                    if len(tail) >= 2 and (full.startswith(tail) or full.endswith(tail)):
                        out.append("%s → склейка «%s» и «%s»" % (cs, head_w, tail))
                        break
    return out
def check_file(path, archive=False):
    """Проверяет один .hol. Возвращает список словарей (file, id, verdict, note).

    archive=True — файл из папки СТАРОЕ: там разрывы ожидаемы (это архив),
    поэтому ОШИБКИ понижаются до предупреждений."""
    p = Path(path)
    rows = []

    def add(cid, verdict, note):
        if archive and verdict == "error":
            verdict = "warn"
            note = "АРХИВ (СТАРОЕ): " + note
        rows.append({"file": p.name, "path": str(p), "id": cid,
                     "verdict": verdict, "note": note})

    if not p.exists():
        add("exists", "error", "файла нет: %s" % p)
        return rows
    if p.stat().st_size == 0:
        add("not_empty", "error", "файл пустой")
        return rows
    add("exists", "ok", "%d байт" % p.stat().st_size)

    text, enc = read_text(p)
    if text is None:
        add("encoding", "error", enc)
        return rows
    add("encoding", "ok", "кодировка %s" % enc)
    lines = text.splitlines()
    sec = find_sections(lines)

    if "TABLE_DATA" not in sec:
        add("table_data", "error", "нет секции TABLE_DATA")
    else:
        add("table_data", "ok", "строка %d" % (sec["TABLE_DATA"] + 1))
    if "THREAD_DATA" not in sec:
        add("thread_data", "error", "нет секции THREAD_DATA")
        return rows
    td = sec["THREAD_DATA"]
    add("thread_data", "ok", "строка %d" % (td + 1))

    # td — индекс (с 0) строки THREAD_DATA; шапка колонок идёт СЛЕДУЮЩЕЙ строкой
    if td + 1 >= len(lines):
        add("head_row", "error", "после THREAD_DATA нет строки")
        return rows
    head, delim = split_cols(lines[td + 1])
    if not head:
        add("head_row", "error", "пустая шапка колонок (строка %d)" % (td + 2))
        return rows
    add("head_row", "ok", "колонок в шапке: %d" % len(head))

    add("fastener_id", "ok" if "FASTENER_ID" in head else "error",
        "FASTENER_ID есть" if "FASTENER_ID" in head else "в шапке нет FASTENER_ID")
    # разделитель: TAB — норма, 2+ пробела — допустимо вендором (живой факт, см. split_cols)
    add("delimiter", "ok" if delim == "TAB" else "warn", "разделитель: %s" % delim)

    broken = broken_names(head)          # ГЛАВНАЯ проверка программы
    add("broken_names", "error" if broken else "ok",
        ("разорваны имена колонок: " + "; ".join(broken)) if broken else "разорванных имён нет")

    unknown = [c.strip() for c in head if c.strip() not in KNOWN]
    add("unknown_cols", "warn" if unknown else "ok",
        "колонок нет в эталоне: %s" % ", ".join(unknown[:5]) if unknown else "все известны эталону")

    data_line = next((l for l in lines[td + 2:] if l.strip()), None)
    if data_line is None:
        add("rows", "warn", "нет строк данных")
        return rows
    cols, _ = split_cols(data_line)
    # при разделителе «2+ пробела» строки данных НЕ разбираются однозначно (значения
    # содержат одинарные пробелы) — это не поломка, поэтому только предупреждение.
    if len(cols) != len(head):
        add("cols_match", "warn" if delim != "TAB" else "error",
            "в шапке %d колонок, в данных %d (разделитель: %s) — сверка ненадёжна"
            % (len(head), len(cols), delim))
    else:
        add("cols_match", "ok", "колонок в данных: %d" % len(cols))
    add("rows", "ok", "строк данных: %d" % len([l for l in lines[td + 3:] if l.strip()]))
    return rows
def scan(dirs=None):
    """Обходит папки с .hol. Возвращает сводку (files, rows, errors, warns, checked)."""
    dirs = [Path(d) for d in (dirs or DEFAULT_DIRS)]
    found, missing = [], []
    for d in dirs:
        if d.exists():
            found += sorted(glob.glob(str(d / "*.hol")))
        else:
            missing.append(str(d))
    rows = []
    for f in found:
        arch = any(part.upper() == "СТАРОЕ" for part in Path(f).parts)
        rows += check_file(f, archive=arch)
    return {"files": found, "missing": missing, "rows": rows,
            "errors": sum(1 for r in rows if r["verdict"] == "error"),
            "warns": sum(1 for r in rows if r["verdict"] == "warn"),
            "checked": len(found)}


def write_report(res, secs=0.0):
    """Отчёт в log\\reports и CSV в log\\hol_check. Возвращает (отчёт, csv)."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d_%H%M%S")
    rp = REPORT_DIR / ("REPORT_hol_check_%s.md" % stamp)
    cp = LOG_DIR / ("hol_check_%s.csv" % stamp)
    out = ["# ОТЧЁТ HOL_CHECK (проверка таблиц отверстий)", "",
           "Файлов проверено: **%d** · ошибок: **%d** · предупреждений: **%d** · %.2f с"
           % (res["checked"], res["errors"], res["warns"], secs), ""]
    if res["missing"]:
        out += ["Папки не найдены (пропущены): " + ", ".join(res["missing"]), ""]
    per = {}
    for r in res["rows"]:
        per.setdefault(r["file"], {"error": 0, "warn": 0, "ok": 0})[r["verdict"]] += 1
    out += ["## Сводка по файлам", "", "| Файл | Ошибок | Предупр. |", "|---|---|---|"]
    for f, v in sorted(per.items()):
        out.append("| %s | %d | %d |" % (f, v["error"], v["warn"]))
    out += ["", "## Подробности (только ошибки и предупреждения)", "",
            "| Файл | Проверка | Вердикт | Что |", "|---|---|---|---|"]
    for r in res["rows"]:
        if r["verdict"] != "ok":
            out.append("| %s | `%s` | %s | %s |"
                       % (r["path"], r["id"], ICON[r["verdict"]], r["note"].replace("|", "/")))
    rp.write_text("\n".join(out), encoding="utf-8")
    with open(cp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["файл", "проверка", "вердикт", "что"])
        for r in res["rows"]:
            w.writerow([r["file"], r["id"], r["verdict"], r["note"]])
    return str(rp), str(cp)


def main(argv):
    dirs = [Path(a) for a in argv[1:]] if len(argv) > 1 else DEFAULT_DIRS
    t0 = time.time()
    res = scan(dirs)
    if not res["files"]:
        print("НЕЧЕГО ПРОВЕРЯТЬ: ни одного .hol в %s" % ", ".join(str(d) for d in dirs))
        for m in res["missing"]:
            print("  папки нет: %s" % m)
        return 2
    secs = time.time() - t0
    print("ПРОВЕРКА ТАБЛИЦ ОТВЕРСТИЙ: файлов %d, ошибок %d, предупреждений %d, %.2f с"
          % (res["checked"], res["errors"], res["warns"], secs))
    for r in res["rows"]:
        if r["verdict"] != "ok":
            print("  %-4s %-22s %-14s %s"
                  % (ICON[r["verdict"]], r["file"], r["id"], r["note"]))
    rp, cp = write_report(res, secs)
    print("-" * 78)
    print("отчёт: %s" % rp)
    print("CSV:    %s" % cp)
    if res["errors"]:
        print("ВЕРДИКТ: ЕСТЬ ОШИБКИ (%d) — Creo может не прочитать эти диаграммы."
              % res["errors"])
        return 1
    print("ВЕРДИКТ: ОК — все диаграммы читаемы.")
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv))