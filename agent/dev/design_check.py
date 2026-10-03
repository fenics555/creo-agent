# -*- coding: utf-8 -*-
"""design_check.py — ПОЛНАЯ ПРОВЕРКА ДИЗАЙНА ОКОН ДОМА (владелец, 03.10.2026).

ЗАЧЕМ. `win_check.py` проверяет 8 окон волны 1 на ПРИСУТСТВИЕ каркаса
(`title/geometry/minsize/README/settings/Thread`). Эта проверка отвечает на вопрос
владельца про ДИЗАЙН целиком и смотрит ВСЕ окна, найденные на диске, а не список.

ПРИЗНАКИ (канон — `D:\\AI\\repo\\ОКНА\\02_ДИЗАЙН_И_РАСКЛАДКА.md` и `SKILL_WINDOWS_GUI.md`):
  ОБЯЗАТЕЛЬНЫЕ: каркас ui_common · title с версией V<N> · geometry · minsize ·
  README-кнопка · тяжёлое в потоке.
  ПРИЗНАКИ КАНОНА (долг, если нет ни в одном окне): LabelFrame-заголовок в ПРОБЕЛАХ ·
  логи Consolas 9 · Treeview(show="headings") · настройки файлом json.
  ЗАПРЕТЫ: путь Creo в коде окна · лог с bg мимо каркаса.

Каждая строка привязана к строке канона, поэтому расхождение — долг с адресом, а не мнение.

Запуск: cmd /c "python -X utf8 dev\\design_check.py > data\\tmp\\design.txt 2>&1"
Отчёт: D:\\AI\\log\\win_check\\design_check_<дата>.txt. RC 0 — окна соответствуют, 1 — есть долги.
"""
import io
import re
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
AGENT = HERE.parent
REPORT_DIR = Path(r"D:\AI\log\win_check")

# Папки, которые окнами НЕ являются (исторические копии, не запускаются).
SKIP_DIRS = {"__pycache__", "data", "_legacy", "_disabled", "log", "node_modules"}


def find_windows():
    """Окна = bat-входы `*_gui.bat` + корневые harvest_gui/purge_gui."""
    wins = []
    for bat in sorted(AGENT.rglob("*gui*.bat")):
        rel = bat.parent
        if SKIP_DIRS & set(rel.parts):
            continue
        name = bat.stem.replace("_gui", "")
        if name in ("harvest", "purge"):
            continue
        gui = None
        for cand in ("gui.py", "%s_gui.py" % name):
            if (rel / cand).is_file():
                gui = rel / cand
                break
        if gui is None:
            # bat может запускать не `gui.py`, а сам движок с окном (plm_reader.bat →
            # plm_reader.py). Берём то, что bat реально запускает, иначе «файла окна нет».
            if bat.is_file():
                txt = bat.read_text(encoding="utf-8", errors="replace")
                m = re.search(r"(?:pythonw?|python -X utf8)?\s*\"?%~dp0([A-Za-z0-9_]+\.py)", txt)
                if m and (rel / m.group(1)).is_file():
                    gui = rel / m.group(1)
        if gui is None:
            g = [p for p in rel.glob("*gui*.py")]
            gui = g[0] if g else None
        if gui is None:
            g = [p for p in rel.glob("*.py") if "gui" in p.read_text(
                encoding="utf-8", errors="replace")[:4000]]
            gui = g[0] if g else None
        wins.append({"name": name, "gui": gui, "bat": bat})
    # Бэкап настроек внутри папки программы — не окно.
    wins = [w for w in wins if w["bat"] and "backup" not in str(w["bat"])]
    for nm, fn in (("harvest", AGENT / "harvest_gui.py"), ("purge", AGENT / "purge_gui.py")):
        if fn.is_file():
            wins.append({"name": nm, "gui": fn, "bat": None})
    return wins


RULES = [
    ("каркас ui_common", True, re.compile(r"import\s+ui_common|from\s+ui_common")),
    ("title с версией V<N>", True, re.compile(r"title\([^)]*V\d+")),
    ("geometry задан", True, re.compile(r"\.geometry\(")),
    ("minsize задан", True, re.compile(r"\.minsize\(")),
    ("README-кнопка", True, re.compile(r"README", re.I)),
    ("тяжёлое в потоке", True, re.compile(r"Thread\(|run_in_thread")),
    ("LabelFrame-заголовок в пробелах", False, re.compile(r'LabelFrame\(\s*text="[^"]*\s[^"]*"')),
    ("логи Consolas 9", False, re.compile(r'Consolas"?\s*,\s*9')),
    ('Treeview(show="headings")', False, re.compile(r'Treeview\([^)]*show="headings"')),
    ("настройки/данные файлом json", False, re.compile(r"settings\.json|rules\.json|load_settings|save_settings")),
]

def _has(src, rx):
    return bool(rx.search(src))


def check_one(src):
    """Возвращает список замечаний по окну.

    УЧТЁМ ЗАКОН КАРКАСА: окно волны 1 выполняет требования не в своём файле, а через
    общий каркас (`U.make_root` даёт title+geometry+minsize, `U.log_view` — моноширинный
    лог, `U.result_tree` — `show="headings"`). Иначе проверка врала бы: она требовала
    от окна дословно повторить то, что каркас уже делает (живая ложь 03.10.2026)."""
    on_card = _has(src, re.compile(r"import\s+ui_common|from\s+ui_common"))
    uses_root = _has(src, re.compile(r"make_root\("))
    uses_log = _has(src, re.compile(r"log_view\("))
    uses_tree = _has(src, re.compile(r"result_tree\("))
    res = []
    if not on_card:
        res.append("каркас ui_common")
    if not (uses_root and re.search(r'V\d+', src)) and not _has(src, re.compile(r"title\([^)]*V\d+")):
        res.append("title с версией V<N>")
    if not uses_root and not _has(src, re.compile(r"\.geometry\(")):
        res.append("geometry задан")
    if not uses_root and not _has(src, re.compile(r"\.minsize\(")):
        res.append("minsize задан")
    if not _has(src, re.compile(r"README", re.I)):
        res.append("README-кнопка")
    if not _has(src, re.compile(r"Thread\(|run_in_thread")):
        res.append("тяжёлое в потоке")
    if not _has(src, re.compile(r'LabelFrame\(\s*text="[^"]*\s[^"]*"')) and not uses_log:
        res.append("LabelFrame-заголовок в пробелах")
    if not _has(src, re.compile(r'Consolas"?\s*,\s*9')) and not uses_log:
        res.append("логи Consolas 9")
    if not _has(src, re.compile(r'Treeview\([^)]*show="headings"')) and not uses_tree:
        res.append('Treeview(show="headings")')
    # Уточнение 03.10.2026: `win_check` для окон на каркасе пишет «settings=ок», потому что
    # настройки ведёт каркас (`ui_common.load_settings/save_settings`), а в коде окна их нет.
    # Требовать от окна буквальный `_settings.json` — ложь. Засчитываем и данные программы
    # файлом (`rules.json`), и настройки через каркас.
    if not (_has(src, re.compile(r"load_settings|save_settings|settings\.json|rules\.json|rules_path"))):
        res.append("настройки/данные файлом json")
    return res


FORBIDDEN = [
    ("путь Creo в коде окна", re.compile(r"Z:\\PTC\\CREO-START|Parametric\\bin\\parametric")),
    ("лог с bg мимо каркаса", re.compile(r'Text\([^)]*bg="#(?!f8f9fa|fbfbfb|f4f4f2)')),
]

# СМЯГЧЕНИЕ ЗАПРЕТА. Найдено 03.10.2026: путь `Z:\PTC\CREO-START\START-STD\config.pro`
# в `config_audit\gui.py:28` и `creo_pdf_gui.py:41` — это НЕ хардкод, а ЗАПАСНОЕ ЗНАЧЕНИЕ
# за общим поиском (`eng.BOOT.config_paths()` / `creo_pdf_env`), и канон прямо требует
# искать общий поиск, а не зашивать путь. Значит запрет звучит только для окна, которое
# НЕ пользуется общим поиском: тогда путь в коде = настоящий хардкод.
CREO_COMMON_SEARCH = re.compile(r"BOOT\.|creo_boot|creo_path|creo_pdf_env|config_paths\(")
def read(w):
    """Текст окна ВМЕСТЕ с подключаемыми им модулями.

    ЖИВАЯ НАХОДКА 03.10.2026: `purge_gui.py` — это ШИМ (510 Б, `runpy.run_path`), он
    перезапускает настоящее окно `purge_versions\\gui.py`; читать только шим бессмысленно.
    И `harvest_gui.py` — только вход, а признаки дизайна (LabelFrame, Consolas, Treeview)
    лежат в подключаемом `harvest_gui_panels.py`. Поэтому текст окна = его файл + все
    `import` локальные модули того же каталога."""
    g = w["gui"]
    if not g or not Path(g).is_file():
        return None
    g = Path(g)
    parts = [g.read_text(encoding="utf-8", errors="replace")]
    # Если файл — шим (маленький и зовёт run_path), берём цель из него.
    if g.stat().st_size < 2000 and "run_path" in parts[0]:
        import re as _re
        m = _re.search(r'run_path\(str\(Path\(__file__\)\.resolve\(\)\.parent\s*/\s*"([^"]+)"',
                       parts[0])
        if m:
            tgt = g.parent / m.group(1) / "gui.py"
            if tgt.is_file():
                g = tgt
                parts = [tgt.read_text(encoding="utf-8", errors="replace")]
    for extra in sorted(g.parent.glob("*.py")):
        if extra == g or extra.stat().st_size > 20000:
            continue
        nm = extra.stem
        if nm in ("gui", "runpy"):
            continue
        try:
            if ("import %s" % nm) in parts[0] or ("from %s" % nm) in parts[0]:
                parts.append(extra.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            pass
    return "\n".join(parts)


def main():
    wins = find_windows()
    rows = []
    total_bad = 0
    print("ПРОВЕРКА ДИЗАЙНА ОКОН ДОМА · найдено окон: %d" % len(wins))
    print("канон: repo\\ОКНА\\02_ДИЗАЙН_И_РАСКЛАДКА.md + SKILL_WINDOWS_GUI.md")
    print("=" * 78)
    for w in wins:
        src = read(w)
        # Текст САМОГО файла входа (без склейки) — для запретов.
        g0 = w["gui"]
        w["own_text"] = (Path(g0).read_text(encoding="utf-8", errors="replace")
                         if g0 and Path(g0).is_file() else "")
        if src is None:
            print("?? %-16s ФАЙЛА ОКНА НЕТ (bat: %s)" % (w["name"], w["bat"]))
            rows.append((w["name"], "НЕТ ФАЙЛА", 0, 0))
            total_bad += 1
            continue
        miss = check_one(src)
        forb = []
        for lab, rx in FORBIDDEN:
            # Запреты смотрим ТОЛЬКО по файлу входа, а не по склейке с подключёнными
            # модулями: ложное срабатывание 03.10.2026 — движок программы в склейке приносил
            # свой путь, а запрет адресован коду ОКНА.
            hay = w.get("own_text") or src
            if not rx.search(hay):
                continue
            if lab == "путь Creo в коде окна" and CREO_COMMON_SEARCH.search(hay):
                continue          # путь стоит ЗА общим поиском — это правильно, не хардкод
            forb.append(lab)
        bad = miss + forb
        total_bad += len(bad)
        print("%s %-16s %s" % ("OK " if not bad else "!! ", w["name"],
                                "нет замечаний" if not bad else "; ".join(bad)))
        rows.append((w["name"], "OK" if not bad else "долги", len(miss), len(forb)))
    print("=" * 78)
    print("СВОДКА ПО ПРИЗНАКАМ (сколько окон НЕ имеют, с учётом каркаса):")
    cnt = {}
    for w in wins:
        s = read(w)
        if s is None:
            continue
        for lab in check_one(s):
            cnt[lab] = cnt.get(lab, 0) + 1
    for lab, _req, _rx in RULES:
        print("   %-34s %2d" % (lab, cnt.get(lab, 0)))
    for lab, rx in FORBIDDEN:
        if lab == "путь Creo в коде окна":
            n = sum(1 for w in wins if (w.get("own_text") or "") and rx.search(w["own_text"])
                    and not CREO_COMMON_SEARCH.search(w["own_text"]))
        else:
            n = sum(1 for w in wins if read(w) is not None and rx.search(read(w)))
        print("   %-34s %2d (запрет)" % ("ЗАПРЕТ: " + lab, n))
    print("=" * 78)
    print("окон с замечаниями: %d · всего замечаний: %d"
          % (sum(1 for r in rows if r[1] not in ("OK", "нет замечаний")), total_bad))
    print("ВЕРДИКТ: %s" % ("ОКНА СООТВЕТСТВУЮТ КАНОНУ" if total_bad == 0
                           else "ЕСТЬ ДОЛГИ ДИЗАЙНА — см. сводку выше"))
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rf = REPORT_DIR / ("design_check_%s.txt" % time.strftime("%Y-%m-%d_%H%M%S"))
    with open(rf, "w", encoding="utf-8") as f:
        f.write("ПРОВЕРКА ДИЗАЙНА ОКОН · %s · окон: %d · замечаний: %d\n"
                % (time.strftime("%Y-%m-%d %H:%M"), len(wins), total_bad))
        for nm, st, m, fb in rows:
            f.write("  %-16s %s (не хватает %d, запретов %d)\n" % (nm, st, m, fb))
    print("отчёт: %s" % rf)
    return 1 if total_bad else 0


if __name__ == "__main__":
    sys.exit(main())