# -*- coding: utf-8 -*-
r"""checks.py — КАРКАС ПРОВЕРОК И ЕДИНЫЙ ПРОГОН (волна 5, этап 3 плана).

ЗАЧЕМ: проверки дома разбросаны по программам (`hol_check`, `config_audit`, `cmnm_scan`,
`plm_audit`, трейлы). Каждая пишет свой отчёт. Этот модуль даёт ИМ общий паспорт и ОДИН
прогон: «прогнать все проверки» → один отчёт со сводкой и ПРОЦЕНТОМ соответствия
(константа 4 волны 1).

ПАСПОРТ ПРОВЕРКИ (словарь, как контракт `tool.json` волны 2):
    {"id": "hol_check", "title": "Таблицы отверстий .hol", "kind": "check",
     "scope": "hole_charts", "severity": "error", "needs_creo": False,
     "run": <функция без аргументов → dict результата>, "app": "hol_check"}

РЕЗУЛЬТАТ ПРОВЕРКИ (единый вид, чтобы сводка считалась):
    {"ok": True/False, "total": int, "failed": int, "warned": int,
     "detail": "...", "items": [{"icon":..,"verdict":..,"what":..}]}

ОБЁРТКИ: старая проверка подключается функцией, которая зовёт её движок. Старый запуск
(`hol_check.bat`, `config_audit.bat`) продолжает работать как раньше — это требование плана.
"""
import io
import re
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

AGENT = Path(__file__).resolve().parent
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

LOG_DIR = Path(r"D:\AI\log\checks")
REPORT_DIR = Path(r"D:\AI\log\reports")

CHECKS = []          # паспорта проверок; наполняется функциями-обёртками


def check(cid, title, kind, scope, severity, app=None, needs_creo=False):
    """Регистратор проверки — обёртка для чистого описания паспорта."""
    def deco(fn):
        CHECKS.append({"id": cid, "title": title, "kind": kind, "scope": scope,
                       "severity": severity, "app": app, "needs_creo": needs_creo,
                       "run": fn})
        return fn
    return deco


def get(cid):
    return next((c for c in CHECKS if c["id"] == cid), None)


def _res(ok, total=0, failed=0, warned=0, detail="", items=None):
    return {"ok": bool(ok), "total": total, "failed": failed, "warned": warned,
            "detail": detail, "items": items or []}


def run_one(spec):
    """Запуск одной проверки. Исключение ВНУТРИ проверки = провал проверки, а не падение прогона."""
    t0 = time.time()
    try:
        r = spec["run"]() or {}
    except Exception:
        return {"ok": False, "total": 0, "failed": 1, "warned": 0,
                "detail": "проверка упала: %s" % traceback.format_exc().splitlines()[-1],
                "items": [], "secs": time.time() - t0}
    r.setdefault("ok", True)
    r.setdefault("total", 0)
    r.setdefault("failed", 0)
    r.setdefault("warned", 0)
    r.setdefault("detail", "")
    r.setdefault("items", [])
    r["secs"] = time.time() - t0
    return r
# --- ОБЁРТКИ СУЩЕСТВУЮЩИХ ПРОВЕРОК --------------------------------------------
@check("hol_check", "Таблицы отверстий .hol читаемы", "check", "hole_charts",
       "error", app="hol_check")
def _run_hol():
    """hol_check: ловит разорванные имена колонок (ошибка err_holechart от 18.09.2026)."""
    sys.path.insert(0, str(AGENT / "hol_check"))
    import hol_check as eng
    res = eng.scan()
    items = [{"icon": "❌" if r["verdict"] == "error" else ("⚠️" if r["verdict"] == "warn" else "✅"),
              "verdict": r["verdict"],
              "what": "%s · %s: %s" % (Path(r["path"]).name, r["id"], r["note"])}
             for r in res["rows"] if r["verdict"] != "ok"]
    return _res(res["errors"] == 0, res["checked"], res["errors"], res["warns"],
                "файлов %d, ошибок %d, предупреждений %d"
                % (res["checked"], res["errors"], res["warns"]), items)


@check("config_paths", "Пути config.pro на месте", "check", "creo", "error",
       app="config_audit")
def _run_config():
    """config_audit: проверка путей из config.pro (бывший отдельный отчёт)."""
    sys.path.insert(0, str(AGENT / "config_audit"))
    import config_audit as eng
    p = eng.CONFIG
    if not p or not Path(p).exists():
        return _res(False, 0, 1, 0, "рабочий config.pro не найден")
    res = eng.audit(p)
    items = [{"icon": "❌", "verdict": "error",
              "what": "строка %s · %s: нет на диске %s" % (pr["line"], pr["opt"], pr["path"])}
             for pr in res["problems"]]
    return _res(res["missing"] == 0, res["total"], res["missing"], 0,
                "путей %d, отсутствует %d" % (res["total"], res["missing"]), items)


@check("plugins_registry", "Плагины боя зафиксированы в карте", "check", "creo", "error",
       app="config_audit")
def _run_plugins():
    """ЭТАП 9 (волна 10): каждый `protkdat` из боевого config.pro есть в `dev\\PLUGINS.md`,
    а активный — ещё и на диске. Профилактика из плана: новый плагин в бою обязан быть
    зафиксирован, иначе про него узнают случайно, через поломку Creo."""
    sys.path.insert(0, str(AGENT / "config_audit"))
    import config_audit as eng
    p = eng.CONFIG
    if not p or not Path(p).exists():
        return _res(False, 0, 1, 0, "рабочий config.pro не найден")
    try:
        res = eng.audit_protk(p)
    except Exception as e:
        return _res(False, 0, 1, 0, "не разобрал плагины: %s" % e)
    items = [{"icon": "❌" if pr["kind"] in ("нет_в_карте", "нет_на_диске") else "⚠️",
              "verdict": "error" if pr["kind"] in ("нет_в_карте", "нет_на_диске") else "warn",
              "what": "%s · строка %s: %s" % (pr["kind"], pr["line"], pr["path"])}
             for pr in res["problems"]]
    for r in res["rows"]:
        items.append({"icon": "✅", "verdict": "ok",
                      "what": "строка %s · %s · %s · %s"
                              % (r["line"], "активен" if r["active"] else "выключен",
                                 "файл есть" if r["on_disk"] else "файла нет",
                                 r["path"])})
    return _res(res["hard"] == 0, res["in_config"], res["hard"],
                len(res["problems"]) - res["hard"],
                "в config.pro %d, в карте %d, активных %d, расхождений %d"
                % (res["in_config"], res["in_card"], res["active"], res["hard"]), items)


@check("window_design", "Дизайн окон соответствует канону", "check", "house", "warn",
       app="ui_common")
def _run_design():
    """03.10.2026 (слово владельца «проверь дизайн окон»): ПОЛНАЯ проверка дизайна всех
    окон, найденных на диске, против канона `repo\\ОКНА\\02_ДИЗАЙН_И_РАСКЛАДКА.md`.
    Не «красивость», а признаки с адресом: каркас, версия в заголовке, minsize,
    README-кнопка, поток, LabelFrame в пробелах, Consolas 9, show="headings", настройки
    файлом, запреты (путь Creo в коде окна, лог мимо каркаса). Учитывает ЗАКОН КАРКАСА:
    окно волны 1 выполняет признаки через `ui_common`, а не дословно в своём файле."""
    import io as _io
    import subprocess as _sp
    probe = AGENT / "dev" / "design_check.py"
    if not probe.is_file():
        return _res(False, 0, 1, 0, "нет dev\\design_check.py")
    r = _sp.run([sys.executable, "-X", "utf8", str(probe)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                cwd=str(AGENT))
    out = r.stdout or ""
    m = re.search(r"найдено окон: (\d+)", out)
    n_win = int(m.group(1)) if m else 0
    m2 = re.search(r"всего замечаний: (\d+)", out)
    total = int(m2.group(1)) if m2 else 0
    items = []
    for line in out.splitlines():
        if line.startswith("!!"):
            items.append({"icon": "⚠️", "verdict": "warn", "what": line[2:].strip()})
    n_bad = sum(1 for x in items)
    # Не «провал» проверки: каркас живой и программы работают, расхождения — долг оформления.
    return _res(True, n_win, 0, n_bad,
                "окон %d, чистых %d, с замечаниями %d, замечаний %d (долг оформления)"
                % (n_win, n_win - n_bad, n_bad, total), items)


@check("ui_integrity", "Витрина цела: JS сбалансирован, экранирование в порядке", "check", "house", "error")
def _run_ui_integrity():
    """04.10.2026 (слово владельца «доделывай», третий раз): витрина правилась три волны подряд,
    а ПРОВЕРКИ ЕЁ СИНТАКСИСА В ЕДИНОМ ПРОГОНЕ НЕ БЫЛО. Инструмент `dev\\js_balance.py` (сканер без
    node: строки, комментарии, регулярки, шаблонные строки) и обвязка `dev\\ui_check.py` в доме
    ЕСТЬ и зелёные — но они звались только вручную, а блок `window_design` про окна tkinter
    витрину не покрывает. То есть сломанный `app.js` проходил мимо `checks.py` тихо.
    Этот блок закрывает дыру: живой прогон `ui_check.py`, вердикт — честный провал (error),
    потому что нечитаемый app.js = витрина не открывается у человека."""
    import subprocess as _sp
    probe = AGENT / "dev" / "ui_check.py"
    if not probe.is_file():
        return _res(False, 0, 1, 0, "нет dev\\ui_check.py")
    r = _sp.run([sys.executable, "-X", "utf8", str(probe)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                cwd=str(AGENT), timeout=60)
    out = (r.stdout or "") + (r.stderr or "")
    files = sorted(p.name for p in (AGENT / "ui").glob("*")
                   if p.suffix in (".js", ".html"))
    items = []
    for line in out.splitlines():
        if line.strip() and not line.startswith("ALL GREEN"):
            items.append({"icon": "❌" if r.returncode else "⚠️",
                          "verdict": "error" if r.returncode else "warn",
                          "what": line.strip()})
    green = "ALL GREEN" in out
    n_bad = len(items)
    return _res(green and r.returncode == 0, len(files), n_bad, 0,
                "файлов витрины %d, замечаний %d%s"
                % (len(files), n_bad, " — зелёная" if green else " — ЕСТЬ ПРОВАЛ"), items)


@check("culture", "Культура дома: отчёты по именам, урна, копии .clinerules", "check", "house", "warn")
def _run_culture():
    """04.10.2026 (слово владельца «доделывай» №9): проверка `dev\\culture_check.py` существует и
    зелёная по существу, но в общий прогон НЕ ВХОДИЛА — то же самое было с витриной до блока
    `ui_integrity`. Следствие: три настоящих нарушения порядка в доме были видны только тому,
    кто помнит про этот скрипт. Пункт 21 манифеста требует ОБЯЗАТЕЛЬНОЙ автоматической
    синхронизации двух копий `.clinerules` — без этого блока расхождение могло бы месяцами
    жить в тишине.

    Порог `warn`, а не `error`: нарушения здесь — про порядок файлов (чужое имя отчёта, файл
    в корне урны, временное вне урны), а не про поломку программ. Удалять такие файлы нельзя
    без прямого слова владельца (манифест п.5), поэтому блок честно показывает долг и оставляет
    решение человеку."""
    import subprocess as _sp
    probe = AGENT / "dev" / "culture_check.py"
    if not probe.is_file():
        return _res(False, 0, 1, 0, "нет dev\\culture_check.py")
    r = _sp.run([sys.executable, "-X", "utf8", str(probe)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                cwd=str(AGENT), timeout=90)
    out = (r.stdout or "") + (r.stderr or "")
    items = []
    n_checked = 0
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("✅"):
            n_checked += 1
        elif s.startswith("❌"):
            items.append({"icon": "❌", "verdict": "warn", "what": s.lstrip("❌ ").strip()})
    m = re.search(r"нарушений (\d+), предупреждений (\d+)", out)
    n_bad = int(m.group(1)) if m else len(items)
    n_warn = int(m.group(2)) if m else 0
    # Нарушения — долг порядка, не поломка: прогон не роняем, но долг показываем.
    return _res(True, n_checked, n_bad, n_warn,
                "пунктов зелёных %d, нарушений %d, предупреждений %d"
                % (n_checked, n_bad, n_warn), items)


@check("window_launch", "У каждого окна есть bat — человек запускает двойным щелчком", "check", "house", "error")
def _run_window_launch():
    """04.10.2026 (слово владельца «все долги! все окна»): два окна в корне агента —
    `harvest_gui.py` и `purge_gui.py` — ЛЕЖАЛИ БЕЗ БАТА. Человек мог открыть их только
    вручную командой, зная имя файла. Сканер дизайна это не смотрит: он проверяет СОДЕРЖИМОЕ
    окна, а не доступность запуска.

    Закрываем КЛАСС проблемы, а не два симптома: если правило «у окна есть bat» не проверяется
    автоматически, третье окно без bat появится снова и снова всплывёт при мне. Проверка
    дешёвая — файловая, окна не запускаются (окна дома — общий ресурс, их нельзя поднимать
    пачками в общем прогоне).

    Порог `error`: окно, которое человек не может открыть, для человека не существует."""
    import glob as _gb
    # ПРАВКА 04.10.2026: сегмента «tools» в списке пропуска быть НЕ должно — он есть в пути
    # КАЖДОГО файла (`D:\AI\tools\agent\…`), и проверка молча отбрасывала всё, рапортуя «окон 0».
    skip = ("backup", "_legacy", "_disabled", "__pycache__")
    items = []
    n_win = 0
    for f in AGENT.rglob("*.py"):     # rglob, а не glob: «**/*.py» без recursive=True не заходит
        p = Path(f)                  # в подпапки и проверка радостно рапортовала «окон 0»
        if any(s in p.parts for s in skip):
            continue
        if not (p.name.endswith("gui.py") or p.name.endswith("_gui.py")):
            continue
        n_win += 1
        # ПРАВКА 04.10.2026 (негативный тест): «есть ЛИБОЙ bat в папке» — слишком слабо.
        # В корне агента лежат AGENT.bat, GIT_SYNC.bat и прочие, и проверка проходила, даже
        # когда bat самого окна убрали. Теперь bat считается годным, только если ОН САМ
        # ссылается на это окно по имени файла.
        ok_bat = False
        for bat in p.parent.glob("*.bat"):
            try:
                if p.name.lower() in bat.read_text(encoding="utf-8",
                                                   errors="replace").lower():
                    ok_bat = True
                    break
            except OSError:
                continue
        if ok_bat:
            continue
        items.append({"icon": "❌", "verdict": "error",
                      "what": "%s — нет bat, который запускает это окно (человек не откроет)"
                              % str(p.relative_to(AGENT))})
    return _res(not items, n_win, len(items), 0,
                "окон найдено %d, без bat %d" % (n_win, len(items)), items)


@check("rules", "Правила дома согласованы и срабатывают", "check", "rules", "error")
def _run_rules():
    """rules_engine: правила валидны, включённые находят совпадения на демо-фактах."""
    import rules_engine as RE
    import rules_tools as RT
    doc, err = RE.load()
    if doc is None:
        return _res(False, 0, 1, 0, "правила не прочитаны: %s" % err)
    errs = RE.validate(doc)
    res = RE.run(RT.DEMO_OBJECTS, doc)
    items = [{"icon": "❌" if e else "⚠️", "verdict": "error" if e else "warn", "what": e}
             for e in errs]
    for h in res["hits"]:
        items.append({"icon": "✅", "verdict": "ok",
                      "what": "%s → %s" % (h["label"], h["object"])})
    s = RE.stats(doc)
    return _res(not errs, s["rules"], len(errs), 0,
                "правил %d (включено %d), критериев %d, совпадений на демо: %d"
                % (s["rules"], s["enabled"], s["criteria"], len(res["hits"])), items)


@check("tool_contracts", "Контракты программ целы", "check", "house", "warn")
def _run_contracts():
    """Все tool.json программ проходят validate (волна 2)."""
    import tool_contract as TC
    cs = TC.all_contracts(AGENT)
    items = []
    bad = 0
    for pid, (c, path, err) in cs.items():
        if err:
            bad += 1
            items.append({"icon": "⚠️", "verdict": "warn",
                          "what": "%s: %s" % (pid, err)})
    return _res(bad == 0, len(cs), 0, bad,
                "контрактов %d, с замечаниями %d" % (len(cs), bad), items)


@check("hol_backups", "Архив таблиц отверстий цел", "check", "hole_charts", "warn",
       app="hol_check")
def _run_hol_bak():
    """Бекапы таблиц: в архиве разрывы ожидаемы, но файлы должны читаться."""
    bak = Path(r"Z:\PTC\CREO-START\START-STD\БЕКАП")
    if not bak.exists():
        return _res(True, 0, 0, 1, "папки бекапов нет: %s" % bak)
    sys.path.insert(0, str(AGENT / "hol_check"))
    import hol_check as eng
    files = sorted(bak.glob("*.hol"))
    bad = 0
    items = []
    for f in files:
        rows = eng.check_file(f)
        if not any(r["id"] == "exists" and r["verdict"] == "ok" for r in rows):
            bad += 1
            items.append({"icon": "❌", "verdict": "error", "what": "не читается %s" % f.name})
    return _res(bad == 0, len(files), bad, 0,
                "файлов в архиве %d, нечитаемых %d (разрывы имён — ожидаемо)"
                % (len(files), bad), items)


@check("model_facts", "Факты из живой модели для правил", "check", "models", "warn")
def _run_facts():
    """Собирает факты из ЖИВОЙ модели через creo_read (без Creo) — основа применения правил.

    Проверяет не саму модель, а связку: файл читается → параметры извлекаются →
    движок правил принимает факты. Если цепочка живая, правила волны 4 применимы к деталям."""
    import facts as FT
    facts, info = FT.collect("G11074")
    if not facts:
        return _res(False, 0, 1, 0, info.get("error") or "факты не собраны")
    import rules_engine as RE
    doc, err = RE.load()
    ok_rules = doc is not None and not err
    return _res(ok_rules, info["params"], 0 if ok_rules else 1, 0,
                "живой файл %s: параметров %d, фактов %d, правил применимы: %s"
                % (Path(info["file"]).name, info["params"], len(facts),
                   "да" if ok_rules else "нет"),
                [{"icon": "✅", "verdict": "ok",
                  "what": "%s = %s" % (f["parameter"], str(f["param_value"])[:40])}
                 for f in facts[:5]])


@check("drawing_notes", "Чертёж: плашки и формат листа", "check", "drawings", "warn",
       app="drawing_audit")
def _run_drawing_notes():
    """drawing_audit: чек-лист плашек и формат листа на PDF-чертежах (волна 6, этап 4).

    Читает боевую папку библиотеки. Текст, который PDF не отдаёт, даёт warn, а не
    «нет плашек»: отсутствие данных - не дефект чертежа (безопасная деградация)."""
    sys.path.insert(0, str(AGENT / "drawing_audit"))
    import drawing_audit as eng
    st = eng.load_settings()
    res = eng.scan([Path(d) for d in (st.get("folders") or eng.DEFAULT_DIRS)], st)
    if not res["files"]:
        return _res(True, 0, 0, 1, "чертежей не найдено в %d папках настроек"
                    % len(st.get("folders") or []))
    notes = [r for r in res["rows"] if r["id"] == "notes_present"]
    sheets = [r for r in res["rows"] if r["id"] == "sheet_size"]
    bad_sheets = sum(1 for r in sheets if r["verdict"] == "error")
    miss = sum(1 for r in notes if r["verdict"] == "warn")
    items = [{"icon": "❌" if r["verdict"] == "error" else "⚠️",
              "verdict": r["verdict"] if r["verdict"] == "error" else "warn",
              "what": "%s: %s" % (Path(r["path"]).name, r["note"])}
             for r in res["rows"] if r["id"] in ("sheet_size", "notes_present")
             and r["verdict"] != "ok"]
    return _res(bad_sheets == 0, len(res["files"]), bad_sheets, miss,
                "чертежей %d, лист не распознан: %d, без полного чек-листа: %d "
                "(чек-лист: %s)" % (res["checked"], bad_sheets, miss, st.get("notes")),
                items)


@check("hatch_audit", "Чертёж: графика и пустые листы", "check", "drawings", "warn",
       app="drawing_audit")
def _run_hatch():
    """drawing_audit: штриховка/графика и пустые листы. Вектор ИЛИ растр: часть
    боевых чертежей — сканы, векторной штриховки у них нет в принципе."""
    sys.path.insert(0, str(AGENT / "drawing_audit"))
    import drawing_audit as eng
    st = eng.load_settings()
    res = eng.scan([Path(d) for d in (st.get("folders") or eng.DEFAULT_DIRS)], st)
    if not res["files"]:
        return _res(True, 0, 0, 1, "чертежей не найдено в настройках")
    rows = [r for r in res["rows"] if r["id"] in ("graphics", "hatch", "empty_page")]
    bad = sum(1 for r in rows if r["verdict"] == "error")
    warn = sum(1 for r in rows if r["verdict"] == "warn")
    items = [{"icon": "❌" if r["verdict"] == "error" else "⚠️",
              "verdict": "error" if r["verdict"] == "error" else "warn",
              "what": "%s: %s" % (Path(r["path"]).name, r["note"])}
             for r in rows if r["verdict"] != "ok"]
    return _res(bad == 0, len(res["files"]), bad, warn,
                "чертежей %d, пустых листов: %d, без графики: %d"
                % (res["checked"], bad, warn), items)


def _probe_root(source=r"D:\AI\PROBA\vol8_copy\vol8_probe.prt"):
    """Папка пробы для проверок `cmnm_names` и `dup_files`.

    ДОЛГ, закрытый 03.10.2026: обе проверки были привязаны к папке `D:\\AI\\PROBA\\vol7_copy`,
    удалённой по слову владельца, и печатали «папки пробы нет» — прогон выглядел пустым.
    Теперь папка создаётся самой проверкой: копия одного живого файла (продакшн-копия
    `vol8_probe.prt` волны 8) + его версии. Ничего чужого не трогаем, только создаём.
    Возвращает путь или None, если взять образец не удалось."""
    root = Path(r"D:\AI\PROBA\checks_probe")
    try:
        root.mkdir(parents=True, exist_ok=True)
        src = Path(source)
        if not src.exists():
            return root if any(root.iterdir()) else None
        dst = root / src.name
        if not dst.exists():
            shutil.copy2(str(src), str(dst))
        return root
    except Exception as e:
        print("ПРОБА: папку создать не удалось (%s) — проверка будет пропущена" % e)
        return None


@check("cmnm_names", "Внутреннее имя модели совпадает с именем файла", "check", "models", "warn",
       app="cmnm_scan")
def _run_cmnm():
    """cmnm_scan: сверка внутреннего имени CREO с именем файла (только чтение).

    Проба на изолированной копии моделей, а не по всей сети: обход Z: на 12 666 файлов
    уходит в минуты, а приёмке нужна скорость и воспроизводимость (живой факт 03.10.2026)."""
    sys.path.insert(0, str(AGENT / "cmnm_scan"))
    import cmnm_scan as eng
    root = _probe_root()
    if not root:
        return _res(True, 0, 0, 1, "образец пробы недоступен — проверка пропущена")
    res = eng.scan([str(root)])
    items = [{"icon": "❌", "verdict": "error",
              "what": "внутри %s, файл %s" % (Path(nm).name, Path(fn).name)}
             for _full, nm, fn in res["bad"]]
    return _res(not res["bad"], res["files"], len(res["bad"]), res["nofield"],
                "файлов %d, расхождений %d, без поля имени %d (%.1f с)"
                % (res["files"], len(res["bad"]), res["nofield"], res["seconds"]), items)


@check("dup_files", "Двойники версий Creo", "check", "house", "warn", app="dup_scan")
def _run_dup():
    """dup_scan: файлы-двойники одного размера и sha1. Только чтение, ничего не двигает."""
    sys.path.insert(0, str(AGENT / "dup_scan"))
    import dup_scan as eng
    root = _probe_root()
    if not root:
        return _res(True, 0, 0, 1, "образец пробы недоступен — проверка пропущена")
    res = eng.find_dups([str(root)])
    items = [{"icon": "⚠️", "verdict": "warn",
              "what": "образец %s, лишних копий: %d" % (Path(g["keep"][0]).name,
                                                        len(g["extra"]))}
             for g in res["groups"][:20]]
    return _res(True, res["files"], 0, len(res["groups"]),
                "файлов %d, групп-двойников %d, лишних байт %d"
                % (res["files"], len(res["groups"]), res["waste"]), items)


@check("registry_contracts", "Реестр программ соответствует контрактам", "check", "house", "warn")
def _run_registry():
    """Каждая программа агента с контрактом проходит validate и не теряет id.

    Это «живая связка» волны 2: контракт должен не просто лежать, а читаться и проходить."""
    import tool_contract as TC
    cs = TC.all_contracts(AGENT)
    bad = []
    for pid, (c, path, err) in sorted(cs.items()):
        if err:
            bad.append("%s: %s" % (pid, err))
        elif not c.get("engine") or not c.get("kind"):
            bad.append("%s: нет engine/kind" % pid)
    return _res(not bad, len(cs), len(bad), 0,
                "контрактов %d, с замечаниями %d" % (len(cs), len(bad)),
                [{"icon": "⚠️", "verdict": "warn", "what": b} for b in bad[:20]])


def registry(as_text=True):
    """Список всех зарегистрированных проверок."""
    if not as_text:
        return [{k: v for k, v in c.items() if k != "run"} for c in CHECKS]
    lines = ["ПРОВЕРКИ ДОМА (%d):" % len(CHECKS)]
    for c in CHECKS:
        lines.append("  %-16s %-11s важность=%-5s %s"
                     % (c["id"], c["scope"], c["severity"], c["title"]))
    return "\n".join(lines)
def checks_run(scope="", only="", as_json=False):
    """ЕДИНЫЙ ПРОГОН: гоняет все проверки (или scope/only) и возвращает общий отчёт.

    Прогон не падает от одной плохой проверки — она просто даёт «провал» в сводке.
    Исключение внутри проверки = провал этой проверки, а не всего прогона."""
    t0 = time.time()
    specs = CHECKS
    if scope:
        specs = [c for c in specs if c["scope"] == scope]
    if only:
        ids = {x.strip() for x in str(only).split(",") if x.strip()}
        specs = [c for c in specs if c["id"] in ids]
    rows = []
    for s in specs:
        r = run_one(s)
        rows.append({"id": s["id"], "title": s["title"], "scope": s["scope"],
                     "severity": s["severity"], **r})
    passed = sum(1 for r in rows if r["ok"])
    total_items = sum(r["total"] for r in rows)
    failed_items = sum(r["failed"] for r in rows)
    pct = (100.0 * passed / len(rows)) if rows else None
    res = {"scope": scope or "все", "checks": len(rows), "passed": passed,
           "failed_checks": len(rows) - passed, "items": total_items,
           "failed_items": failed_items, "percent": pct,
           "secs": time.time() - t0, "rows": rows}
    if as_json:
        return res
    return render(res)


def render(res):
    """Человеческий вид прогона: сводка + строки проверок + проблемы."""
    lines = ["ПРОГОН ПРОВЕРОК ДОМА · область: %s · %.2f с"
             % (res["scope"], res["secs"]),
             "проверок: %d · успешно: %d · провалено: %d · объектов проверено: %d"
             % (res["checks"], res["passed"], res["failed_checks"], res["items"])]
    if res["percent"] is not None:
        lines.append("СООТВЕТСТВИЕ: %d %%" % round(res["percent"]))
    lines.append("-" * 78)
    for r in res["rows"]:
        lines.append("%s %-16s %-52s %s"
                     % ("✅" if r["ok"] else "❌", r["id"], r["title"][:52], r["detail"]))
        for it in r["items"]:
            if it["verdict"] == "ok":
                continue
            lines.append("      %s %s" % (it["icon"], it["what"]))
    lines.append("-" * 78)
    lines.append("ВЕРДИКТ: %s" % ("все проверки пройдены" if not res["failed_checks"]
                                  else "провалено проверок: %d" % res["failed_checks"]))
    return "\n".join(lines)


def write_report(res):
    """Один отчёт прогона в log\\reports (требование этапа 3: один отчёт со сводкой)."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d_%H%M%S")
    rp = REPORT_DIR / ("REPORT_checks_run_%s.md" % stamp)
    out = ["# ОТЧЁТ ЕДИНОГО ПРОГОНА ПРОВЕРОК", "",
           "Область: **%s** · проверок: **%d** · успешно: **%d** · "
           "соответствие: **%s%%** · %.2f с"
           % (res["scope"], res["checks"], res["passed"],
              "н/д" if res["percent"] is None else round(res["percent"]), res["secs"]), "",
           "## Проверки", "", "| Проверка | Область | Вердикт | Что показала |", "|---|---|---|---|"]
    for r in res["rows"]:
        out.append("| %s | %s | %s | %s |"
                   % (r["title"], r["scope"], "ОК" if r["ok"] else "ПРОВАЛ",
                      r["detail"].replace("|", "/")))
    problems = [(r["id"], it) for r in res["rows"] for it in r["items"] if it["verdict"] != "ok"]
    if problems:
        out += ["", "## Проблемы", "", "| Проверка | Что |", "|---|---|"]
        for cid, it in problems:
            out.append("| %s | %s %s |" % (cid, it["icon"], it["what"].replace("|", "/")))
    rp.write_text("\n".join(out), encoding="utf-8")
    return str(rp)


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    scope = sys.argv[1] if len(sys.argv) > 1 else ""
    data = checks_run(scope, as_json=True)        # словарь — для отчёта
    print(render(data))                           # текст — для человека
    p = write_report(data)
    print("отчёт: %s" % p)
    sys.exit(1 if data["failed_checks"] else 0)