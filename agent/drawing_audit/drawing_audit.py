# -*- coding: utf-8 -*-
r"""drawing_audit.py - АУДИТ ЧЕРТЕЖА БЕЗ CREO (волна 6, этап 4 плана). Класс Р.

Что делает: читает PDF-чертежи и по чек-листу ИЗ НАСТРОЕК проверяет
  - формат листа (A4...A0, альбом/книжн);
  - читаемость текста (в части файлов нет карты шрифта - это warn, а не выдумка);
  - наличие обязательных плашек (чек-лист: ГОСТ, ЛИСТ, МАССА, МАСШТАБ, АВТОР, ТВОР.);
  - наличие графики (вектор/растр) - пустой лист = ошибка;
  - плотность штриховки (страниц с графикой не меньше порога);
  - пустые страницы.

ЧЕГО НЕ ДЕЛАЕТ: не рисует и не правит чертежи (прямой запрет плана: штриховка - дело Creo),
не лезет в .drw за параметрами - живая проба дала там 0 параметров (спека волны 6, п.3).

ЖИВАЯ ПРОВЕРКА 03.10.2026: эталон
`Z:\PTC\CREO-START\Libraries\Библиотека_стандартных_изделий\Заклепки\pdf\10301-80.pdf`
-> 3 страницы, лист 842x595 (A3 альбом), читается "ГОСТ 10301-80 (СТ СЭВ 1022-78)",
векторных примитивов на стр.3 - 2401.

Запуск: drawing_audit.bat [папка]
RC 0 - замечаний нет | 1 - есть ошибки | 2 - нечего проверять
"""
import csv
import io
import json
import os
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_AGENT = _HERE.parent
for _p in (_AGENT, _HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

LOG_DIR = Path(r"D:\AI\log\drawing_audit")
REPORT_DIR = Path(r"D:\AI\log\reports")
SETTINGS = _AGENT / "data" / "drawing_audit_settings.json"

# Боевые папки с PDF-чертежами библиотеки стандартных изделий (проба 03.10.2026).
LIB = Path(r"Z:\PTC\CREO-START\Libraries\Библиотека_стандартных_изделий")
DEFAULT_DIRS = [LIB / "Заклепки" / "pdf", LIB / "Болты_винты" / "pdf",
                LIB / "Гайки" / "pdf", LIB / "Шайбы" / "pdf"]
ETALON = LIB / "Заклепки" / "pdf" / "10301-80.pdf"

# Форматы листов ISO A, мм: (короткая, длинная). Ориентацию определяем сами.
SHEETS = {"A0": (841, 1189), "A1": (594, 841), "A2": (420, 594),
          "A3": (297, 420), "A4": (210, 297), "A5": (148, 210)}
TOL = 8                 # допуск по мм: печать с полями съедает размер
PT2MM = 25.4 / 72.0

# Чек-лист плашек. ЖИВАЯ ПРОВЕРКА 03.10.2026 (log\urn\cline\vol6_notes.txt) на 6 боевых
# PDF ГОСТ из Заклепки\pdf: реально встречаются ГОСТ, СТ, МАСС, ТВОР, ПРОВЕР, ИЗМ.
# Марок ЛИСТ/МАСШТАБ/АВТОР там нет — эти файлы титульные листы стандарта, а не чертежи
# изделий, поэтому в дефолт они НЕ входят (иначе чек-лист врёт на своём же эталоне).
# Полный перечень для боевых чертёжей задаётся файлом настроек, без правки кода.
DEFAULTS = {
    "folders": [str(d) for d in DEFAULT_DIRS],
    "notes": "ГОСТ;СТ;МАСС;ТВОР.;ПРОВЕР;ИЗМ.",
    "hatch_pages": 1,     # столько страниц с графикой считаем «есть штриховка»
    "vector_min": 50,     # меньше примитивов - лист пустой по графике
    "show_ok": "нет",
    "preview": "нет",
}
ICON = {"error": "FAIL", "warn": "WARN", "ok": "OK"}


def load_settings():
    """Настройки из файла; чего нет - дефолт. Ничего не выдумывает."""
    d = dict(DEFAULTS)
    try:
        if SETTINGS.exists():
            d.update(json.loads(SETTINGS.read_text(encoding="utf-8")))
    except Exception:
        pass
    return d


def save_settings(vals):
    """Запись настроек чек-листа: файл настроек, а не правка кода."""
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(vals, ensure_ascii=False, indent=1), encoding="utf-8")
    return str(SETTINGS)


def sheet_of(width_mm, height_mm):
    """Формат листа по габаритам: (имя, ориентация) либо ('н/д', причина)."""
    w, h = (width_mm, height_mm) if width_mm >= height_mm else (height_mm, width_mm)
    best, delta = "н/д", 1e9
    for name, (a, b) in SHEETS.items():
        d = min(abs(w - a) + abs(h - b), abs(w - b) + abs(h - a))
        if d < delta:
            best, delta = name, d
    if delta > TOL * 3:
        return "н/д", "неизвестный %.0fx%.0f мм" % (width_mm, height_mm)
    return best, "альбом" if width_mm >= height_mm else "книжн"


def readable(txt):
    """Текст читаемый, если в нём есть осмысленные символы (буквы/цифры).

    В части файлов экспорта нет карты шрифта: pymupdf отдаёт символы с кодами 0x01..0x1f
    вместо букв. Такой текст НЕ считаем пустым плашкой - считаем нечитаемым (warn)."""
    if not txt:
        return False, 0.0
    letters = sum(1 for ch in txt if ch.isalnum() or "\u0400" <= ch <= "\u04ff")
    ratio = letters / max(len(txt), 1)
    return ratio >= 0.3, ratio
def _mupdf_quiet():
    """Глушит сообщения MuPDF в stderr (`cmsOpenProfileFromMem failed`).

    На боевых PDF ГОСТ они сыпатся на каждом файле и заслоняют отчёт, а проверить
    нечего: файл открывается и читается. ЖИВАЯ ПРОВЕРКА 03.10.2026."""
    try:
        import pymupdf
        pymupdf.TOOLS.mupdf_display_errors(False)
    except Exception:
        pass


def check_file(path, st=None):
    """Один чертёж -> список замечаний. Ничего не меняет на диске."""
    st = st or load_settings()
    p = Path(path)
    rows = []
    notes = [x.strip() for x in str(st.get("notes", "")).split(";") if x.strip()]
    try:
        import pymupdf
    except Exception as e:
        return [{"path": str(p), "id": "engine", "verdict": "error",
                 "note": "pymupdf недоступен: %s" % e}]
    _mupdf_quiet()
    try:
        d = pymupdf.open(str(p))
    except Exception as e:
        return [{"path": str(p), "id": "open", "verdict": "error",
                 "note": "не открывается: %s" % e}]
    try:
        pages, full_text = [], []
        for i, pg in enumerate(d):
            txt = " ".join(pg.get_text().split())
            full_text.append(txt)
            try:
                vec = len(pg.get_drawings())
            except Exception:
                vec = 0
            try:
                imgs = len(pg.get_images(full=True))
            except Exception:
                imgs = 0
            wmm, hmm = pg.rect.width * PT2MM, pg.rect.height * PT2MM
            name, orient = sheet_of(wmm, hmm)
            pages.append({"n": i + 1, "text": txt, "vec": vec, "img": imgs,
                          "w": wmm, "h": hmm, "sheet": name, "orient": orient})
    finally:
        d.close()

    joined = " ".join(full_text).upper()
    ok_read, ratio = readable(joined)
    vmin = int(st.get("vector_min", 50))

    bad = [pg["n"] for pg in pages if pg["sheet"] == "н/д"]
    rows.append({"path": str(p), "id": "sheet_size",
                 "verdict": "error" if bad else "ok",
                 "note": ("страницы с неопознанным форматом: %s" % bad) if bad
                         else "формат определён: %s" % ", ".join(
                             sorted({pg["sheet"] for pg in pages}))})
    rows.append({"path": str(p), "id": "text_readable",
                 "verdict": "ok" if ok_read else "warn",
                 "note": "текст читается (доля букв %.0f %%)" % (ratio * 100)
                         if ok_read else
                         "текст не извлекается (доля букв %.0f %%) - у PDF нет карты "
                         "шрифта, плашки по нему не судятся" % (ratio * 100)})
    if ok_read:
        # Сравнение по ОСНОВЕ марки: в тексте часто «ТВОР» без точки, а в чек-листе «ТВОР.».
        # Живая проба 03.10.2026: без этого 10301-80 давал ложное «нет плашек: ТВОР.».
        miss = [n for n in notes if n.upper().rstrip(".") not in joined]
        rows.append({"path": str(p), "id": "notes_present",
                     "verdict": "warn" if miss else "ok",
                     "note": ("нет плашек: %s" % ", ".join(miss)) if miss
                             else "все плашки чек-листа найдены (%d)" % len(notes)})
    else:
        rows.append({"path": str(p), "id": "notes_present", "verdict": "warn",
                     "note": "плашки не судятся: текст не читается (см. text_readable)"})
    # 4. ГРАФИКА. ЛИСТ ПУСТ = нет ни вектора, ни растра, ни текста.
    #    ЛИВАЯ ПРОВЕРКА 03.10.2026 (drw_probe5.txt): в 10299-80.pdf стр.1 имеет вектор 1
    #    (рамка титульного листа ГОСТ) и 167 символов текста — такой лист НЕ пустой.
    #    Первый критерий («вектор < 50 => пустая») давал 2 ложных FAIL на титульных листах.
    blank = [pg["n"] for pg in pages
             if pg["vec"] < vmin and pg["img"] == 0 and len(pg["text"]) < 10]
    rows.append({"path": str(p), "id": "graphics",
                 "verdict": "error" if blank else "ok",
                 "note": ("пустых страниц: %s" % blank) if blank else
                         "пустых страниц нет, графика на %d стр. из %d"
                         % (sum(1 for pg in pages if pg["vec"] >= vmin or pg["img"]),
                            len(pages))})
    # 5. ШТРИХОВКА = графика на листах. Вектор ИЛИ растр: 10302/10303/10304.pdf — сканы
    #    (живая проба vol6_vec.txt: на каждой странице vec1/img7…img12), векторной штриховки
    #    у них нет в принципе, и называть это дефектом было бы враньём.
    vec_pages = sum(1 for pg in pages if pg["vec"] >= vmin)
    img_pages = sum(1 for pg in pages if pg["img"] > 0)
    hatched = sum(1 for pg in pages if pg["vec"] >= vmin or pg["img"] > 0)
    need = int(st.get("hatch_pages", 1))
    if hatched >= need:
        note = "графика на %d стр. из %d (вектор на %d, растр на %d)" \
               % (hatched, len(pages), vec_pages, img_pages)
    else:
        note = "графика только на %d стр. (нужно %d) — чертёж почти пуст" % (hatched, need)
    rows.append({"path": str(p), "id": "hatch",
                 "verdict": "ok" if hatched >= need else "warn", "note": note})
    empty = [pg["n"] for pg in pages
             if pg["vec"] == 0 and pg["img"] == 0 and len(pg["text"]) < 10]
    rows.append({"path": str(p), "id": "empty_page",
                 "verdict": "warn" if empty else "ok",
                 "note": "пустых страниц: %s" % empty if empty else "пустых страниц нет"})
    return rows


def find_files(dirs):
    """PDF-чертежи в папках. os.walk со сверкой вниз: регистр имён в доме разный."""
    out, missing = [], []
    for d in dirs:
        if not d:
            continue
        dp = Path(d)
        if not dp.exists():
            missing.append(str(dp))
            continue
        if dp.is_file():
            if dp.suffix.lower() == ".pdf":
                out.append(str(dp))
            continue
        for dirpath, dirnames, filenames in os.walk(str(dp)):
            low = [f.lower() for f in filenames]
            for i, f in enumerate(low):
                if f.endswith(".pdf"):
                    out.append(os.path.join(dirpath, filenames[i]))
    return sorted(set(out)), missing


def scan(dirs=None, st=None):
    """Обход папок -> сводка прогона (как у hol_check, чтобы отчёт был единообразным)."""
    st = st or load_settings()
    dirs = [Path(d) for d in (dirs or st.get("folders") or DEFAULT_DIRS)]
    files, missing = find_files(dirs)
    rows = []
    for f in files:
        rows += check_file(f, st)
    return {"files": files, "missing": missing, "rows": rows,
            "checked": len(files),
            "errors": sum(1 for r in rows if r["verdict"] == "error"),
            "warns": sum(1 for r in rows if r["verdict"] == "warn")}
def write_report(res, secs=0.0):
    """Отчёт в log\\reports и CSV в log\\drawing_audit. Возвращает (отчёт, csv)."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d_%H%M%S")
    rp = REPORT_DIR / ("REPORT_drawing_audit_%s.md" % stamp)
    cp = LOG_DIR / ("drawing_audit_%s.csv" % stamp)
    out = ["# ОТЧЁТ АУДИТА ЧЕРТЕЖА (drawing_audit, класс Р)", "",
           "Чертежей проверено: **%d** · ошибок: **%d** · предупреждений: **%d** · %.2f с"
           % (res["checked"], res["errors"], res["warns"], secs), ""]
    if res["missing"]:
        out += ["Папки не найдены (пропущены): " + ", ".join(res["missing"]), ""]
    per = {}
    for r in res["rows"]:
        name = r["path"].split("\\")[-1]
        cell = per.setdefault(name, {"error": 0, "warn": 0})
        cell[r["verdict"]] = cell.get(r["verdict"], 0) + 1
    out += ["## Сводка по чертежам", "", "| Чертёж | Ошибок | Предупр. |", "|---|---|---|"]
    for f, v in sorted(per.items()):
        out.append("| %s | %d | %d |" % (f, v.get("error", 0), v.get("warn", 0)))
    out += ["", "## Замечания (только ошибки и предупреждения)", "",
            "| Чертёж | Проверка | Вердикт | Что |", "|---|---|---|---|"]
    for r in res["rows"]:
        if r["verdict"] != "ok":
            out.append("| %s | `%s` | %s | %s |"
                       % (r["path"].split("\\")[-1], r["id"], ICON[r["verdict"]],
                          r["note"].replace("|", "/")))
    rp.write_text("\n".join(out), encoding="utf-8")
    with open(cp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["чертёж", "проверка", "вердикт", "что"])
        for r in res["rows"]:
            w.writerow([r["path"], r["id"], r["verdict"], r["note"]])
    return str(rp), str(cp)


def preview(path, out_dir=None, page=1, dpi=100):
    """Превью-картинка страницы: окну надо показать чертёж глазами."""
    import pymupdf
    out_dir = Path(out_dir or LOG_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    d = pymupdf.open(str(path))
    try:
        idx = max(0, min(int(page) - 1, d.page_count - 1))
        fn = out_dir / ("preview_%s_p%s.png" % (Path(path).stem, idx + 1))
        d[idx].get_pixmap(dpi=int(dpi)).save(str(fn))
        return str(fn)
    finally:
        d.close()


def main(argv):
    dirs = [Path(a) for a in argv[1:]] if len(argv) > 1 else None
    t0 = time.time()
    res = scan(dirs)
    if not res["files"]:
        print("НЕЧЕГО ПРОВЕРЯТЬ: ни одного PDF-чертежа в %s"
              % ", ".join(str(d) for d in (dirs or DEFAULT_DIRS)))
        for m in res["missing"]:
            print("  папки нет: %s" % m)
        return 2
    secs = time.time() - t0
    print("АУДИТ ЧЕРТЕЖА: файлов %d, ошибок %d, предупреждений %d, %.2f с"
          % (res["checked"], res["errors"], res["warns"], secs))
    for r in res["rows"]:
        if r["verdict"] != "ok":
            print("  %-4s %-26s %-14s %s"
                  % (ICON[r["verdict"]], r["path"].split("\\")[-1], r["id"], r["note"]))
    rp, cp = write_report(res, secs)
    print("-" * 78)
    print("отчёт: %s" % rp)
    print("CSV:    %s" % cp)
    if res["errors"]:
        print("ВЕРДИКТ: ЕСТЬ ОШИБКИ (%d)" % res["errors"])
        return 1
    print("ВЕРДИКТ: ОК — ошибок нет (%d предупреждений)" % res["warns"])
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv))