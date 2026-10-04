# -*- coding: utf-8 -*-
r"""plan.py - ПЛАН очистки пост-регенерации, удаления параметров и переименования.

ЗАЧЕМ: работа в Creo необратима, поэтому сначала план - человек видит, ЧТО
будет изменено, и только потом пишет. План здесь СТРОИТСЯ ЧЕРЕЗ CREOSON, потому
что уравнения пост-регенерации лежат внутри модели и по файлу не читаются
(в отличие от обычных параметров).

ТРИ ДЕЙСТВИЯ (каждое выключается отдельно, все с безопасным умолчанием):
  1. postregen - очистить уравнения ПОСТ-РЕГЕНЕРАЦИИ
     (file:postregen_relations_set со списком relations = [] по живой спеке);
  2. params   - удалить параметры по маскам (parameter:delete, маски разрешены);
  3. rename   - переименовать элементы модели по карте СТАРОЕ=НОВОЕ
     (feature:rename; для ВИДОВ НА ЧЕРТЕЖЕ - отдельное действие drawing:rename_view).

ПЛАН НИЧЕГО НЕ ПИШЕТ. Запись - отдельный шаг apply.py и только по согласию.
"""
import io
import json
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_AGENT = _HERE.parent
for _p in (_AGENT, _HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

LOG_DIR = Path(r"D:\AI\log\postregen_clean")
REPORT_DIR = Path(r"D:\AI\log\reports")

# Рабочая зона программы по слову владельца: пробы только в PROBA (см. SKILL_creo_index.md,
# «ЗОНЫ РАБОТЫ С ФАЙЛАМИ»). На Z: - только чтение, поэтому запись идёт на копию.
DEFAULT_ROOT = r"D:\AI\PROBA\postregen_clean"
MAX_FILES = 100


def models_in(root=None, limit=MAX_FILES, mask="*.asm"):
    """Файлы моделей под корнем под маской. os.walk + сверка вниз: в доме имена
    в нижнем регистре (`g11074.prt.1`), а pathlib.rglob сравнивает регистр строго.

    ЖИВАЯ НАХОДКА 04.10.2026: на складе Z:\\PTC\\Work файлы ВЕРСИОНИРОВАНЫ —
    не `00080-03.asm`, а `00080-03.asm.1`. Маска `*.asm` по полному имени их
    не видела, и программа на боевых сборках не находила НИЧЕГО. Поэтому маска
    сверяется и с полным именем, и с именем без номера версии."""
    root = Path(root or DEFAULT_ROOT)
    if not root.exists():
        return [], "папки нет: %s" % root
    import fnmatch
    import os
    import re
    pats = [p.strip() for p in str(mask or "*.*").lower().replace(",", ";").split(";")
            if p.strip()]
    out = []
    for dirpath, _dirs, files in os.walk(str(root)):
        for f in files:
            low = f.lower()
            base = re.sub(r"\.\d+$", "", low)      # имя БЕЗ номера версии
            if not (base.endswith(".prt") or base.endswith(".asm")):
                continue
            if not any(fnmatch.fnmatch(low, p) or fnmatch.fnmatch(base, p)
                       for p in pats):
                continue
            out.append(os.path.join(dirpath, f))
            if len(out) >= int(limit):
                return sorted(out), None
    return sorted(out), None


def parse_pairs(text):
    """'A=B;C=D' -> [('A','B'),('C','D')]. Плохая строка - исключение с текстом."""
    out = []
    for it in str(text or "").replace(",", ";").split(";"):
        s = it.strip()
        if not s:
            continue
        if "=" not in s:
            raise ValueError("запись без «=»: %s (нужно СТАРОЕ=НОВОЕ)" % s)
        k, v = s.split("=", 1)
        if k.strip() and v.strip():
            out.append((k.strip(), v.strip()))
    return out


def parse_masks(text):
    """'LM_*;MP_*' -> ['LM_*','MP_*']. Это маски имён параметров."""
    return [s.strip() for s in str(text or "").replace(",", ";").split(";") if s.strip()]


STOP = {"flag": False}   # флаг СТОП между моделями; кнопка окна ставит его в True


def creoson_url():
    """ЕДИНЫЙ источник адреса CREOSON: настройка агента `creoson_url`.

    АУДИТ 04.10.2026: в коде был зашит порт 8080, а адрес на самом деле живёт
    в settings.get("creoson_url") (creo_tools.py:14). Два источника истины —
    при смене порта проверка стека врала бы. Теперь адрес один."""
    import urllib.parse
    try:
        sys.path.insert(0, _AGENT)
        import settings as S
        url = S.get("creoson_url") or "http://127.0.0.1:8080/creoson"
    except Exception:
        url = "http://127.0.0.1:8080/creoson"
    u = urllib.parse.urlparse(url)
    return u.hostname or "127.0.0.1", int(u.port or 8080)


def drive_is_remote(letter):
    """Тип диска по Windows: сетевой или нет. (ok, чем).

    АУДИТ-НАХОДКА 04.10.2026: проверки «существует ли буква диска» НЕДОСТАТОЧНЫ —
    сетевой диск Z: тоже существует, поэтому `Z:` проходил как локальный. Настоящий
    признак сетевого диска — только GetDriveTypeW: DRIVE_REMOTE (4)."""
    import ctypes
    try:
        t = ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(letter + ":\\"))
    except Exception as e:
        return None, "GetDriveTypeW не ответил: %s" % e
    kinds = {0: "неизвестный", 1: "нет корня", 2: "съёмный", 3: "локальный",
             4: "СЕТЕВОЙ", 5: "CD/DVD"}
    return (t == 4), kinds.get(t, "код %s" % t)


# КОРНИ, КУДА ЗАПИСЬ ЗАПРЕЩЕНА (слово владельца: SKILL_creo_index.md, «ЗОНЫ РАБОТЫ
# С ФАЙЛАМИ» — на Z:\PTC только чтение; пробы только в PROBA).
#
# АУДИТ-НАХОДКА 04.10.2026: думали, что Z: — сетевой диск, и проверяли это по
# GetDriveTypeW. ЖИВАЯ ПРОВЕРКА (wmic logicaldisk) опровергла: у Z: DriveType=3,
# то есть ЛОКАЛЬНЫЙ диск; сетевой в этой машине Y: (\\backup\Public, DriveType=4).
# Значит запрет Z: держится не системой, а только правилом дома — и проверять его
# надо ПО ПУТИ, а не по типу диска.
FORBIDDEN_ROOTS = (r"Z:",)


def _under(path, root):
    """Путь внутри корня? Сравнение без учёта регистра и со слэшами."""
    try:
        p = str(Path(str(path))).replace("\\", "/").rstrip("/").upper()
        r = str(root).replace("\\", "/").rstrip("/").upper()
        return p == r or p.startswith(r + "/")
    except Exception:
        return False


def write_allowed(path, forbidden=None):
    """ЩИТ ЗАПИСИ: можно ли писать в эту модель. Возвращает (можно?, причина).

    АУДИТ 04.10.2026: запрет «на Z: только чтение» был ТОЛЬКО в комментариях и
    README, а кода не было. Теперь запрет настоящий и на двух признаках сразу:
      1) путь внутри запрещённого корня (по умолчанию Z:);
      2) сетевой диск (GetDriveTypeW = DRIVE_REMOTE) или UNC-путь."""
    roots = tuple(forbidden or FORBIDDEN_ROOTS)
    for r in roots:
        if _under(path, r):
            return False, ("корень %s по правилам дома только для чтения — запись запрещена: %s"
                           % (r, path))
    p = Path(str(path))
    raw = str(p)
    if raw.startswith("\\\\") or raw.startswith("//"):
        return False, "сетевой путь UNC не пишется: %s" % raw
    drive = p.drive.rstrip(":").upper()
    import string
    if not drive or drive not in list(string.ascii_uppercase):
        return False, "неизвестный диск %r: %s" % (drive, raw)
    import os
    if not os.path.exists(drive + ":\\"):
        return False, "диска %s: нет на этой машине — запись запрещена: %s" % (drive, raw)
    remote, kind = drive_is_remote(drive)
    if remote:
        return False, "диск %s: %s — запись запрещена: %s" % (drive, kind, raw)
    return True, "диск %s: %s; не в запрещённых корнях (%s)" % (
        drive, kind, ", ".join(roots) or "нет")


def stack_ready(timeout=3):
    """Готов ли стек к работе: (готов?, причина). Честный отказ, а не «успех»."""
    import socket
    host, port = creoson_url()
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect((host, port))
    except Exception:
        return False, "CREOSON не отвечает (%s:%s)" % (host, port)
    finally:
        s.close()
    try:
        import subprocess
        # tasklist отдаёт cp866; при utf-8 reader-thread падает (живой факт 03.10.2026).
        ps = subprocess.run(["tasklist", "/FI", "IMAGENAME eq parametric.exe"],
                            capture_output=True, text=True, encoding="cp866",
                            errors="replace", timeout=20)
        if "parametric.exe" not in (ps.stdout or ""):
            return False, "CREOSON отвечает, но Creo не запущен (parametric.exe нет)"
    except Exception as e:
        return False, "не удалось проверить parametric.exe: %s" % e
    return True, "стек готов: CREOSON отвечает, Creo запущен"


def model_name(path):
    """Имя модели для Creo: без номера версии.

    ЖИВАЯ НАХОДКА 04.10.2026: на складе лежат файлы вида `00080-03.asm.1`.
    Если открыть такой файл по имени как есть — CREOSON отвечает
    «Error: Unknown Model Extension», потому что для Creo расширение тут .asm,
    а .1 он воспринимает как часть имени. В диске файл версионированный,
    а в Creo модель называется БЕЗ номера."""
    import re
    return re.sub(r"\.\d+$", "", str(Path(str(path)).name))


def open_read(path, timeout=30):
    """Открыть модель в сессии ДЛЯ ЧТЕНИЯ. Возвращает (ok, причина).

    ЖИВАЯ НАХОДКА 04.10.2026 (probe_open_active): без открытия
`file:postregen_relations_get` отвечает «File ... was not open». ВТОРАЯ НАХОДКА
той же пробы: при `display:false` модель грузится, но активного окна нет и
`file:get_active` отдаёт пустой `data` {} — поэтому activate нужен БЕЗ
display:false. Открытие само по себе на диск не пишет."""
    import creo_tools as CT
    p = Path(path)
    j = CT.creo_call("file", "open",
                     {"dirname": str(p.parent), "file": model_name(path),
                      "activate": True}, timeout)
    if CT.ok(j):
        return True, "открыта %s" % p.name
    return False, CT.errmsg(j)


def read_postregen(path):
    """Уравнения пост-регенерации одной модели: (ok, список строк, причина).

    Истина о функции - живая спека CREOSON file-postregen_relations_get.json:
    ответ `relations`, массив строк."""
    import creo_tools as CT
    opened, why = open_read(path)
    if not opened:
        return False, [], "модель не открыта: %s" % why
    j = CT.creo_call("file", "postregen_relations_get", {"file": model_name(path)}, 25)
    if not CT.ok(j):
        return False, [], CT.errmsg(j)
    d = (j.get("data") or {}).get("relations") or []
    if isinstance(d, str):
        d = [d]
    return True, [str(x) for x in d if str(x).strip()], ""


def read_params(path):
    """Параметры одной модели (оценка масок): (ok, список имён, причина).

    Открываем модель: параметры читаются у активной/открытой модели
    (живой факт 04.10.2026 — без открытия список пустой)."""
    import creo_tools as CT
    opened, why = open_read(path)
    if not opened:
        return False, [], "модель не открыта: %s" % why
    j = CT.creo_call("parameter", "list", {"file": model_name(path)}, 25)
    if not CT.ok(j):
        return False, [], CT.errmsg(j)
    d = (j.get("data") or {}).get("paramlist") or []
    return True, [str(x.get("name")) for x in d
                  if isinstance(x, dict) and x.get("name")], ""


def read_features(path, mask=None):
    """Имена элементов модели под маской (план переименования)."""
    import creo_tools as CT
    opened, why = open_read(path)
    if not opened:
        return False, [], "модель не открыта: %s" % why
    data = {"file": model_name(path)}
    if mask:
        data["name"] = mask
    j = CT.creo_call("feature", "list", data, 25)
    if not CT.ok(j):
        return False, [], CT.errmsg(j)
    d = (j.get("data") or {}).get("featlist") or []
    return True, [str(x.get("name")) for x in d
                  if isinstance(x, dict) and x.get("name")], ""


def plan_for_file(path, opts):
    """Что изменится в одной модели. Шаги видов: postregen / param / rename."""
    import fnmatch
    name = Path(path).name
    steps = []
    if opts.get("postregen"):
        ok, rels, err = read_postregen(path)
        steps.append({
            "file": path, "name": name, "kind": "postregen",
            "target": "%d уравнений" % len(rels),
            "verdict": ("read_fail" if not ok else ("clear" if rels else "same")),
            "note": err if not ok else (("; ".join(rels))[:300] if rels
                                        else "пострегенерация пуста — трогать нечего")})
    for m in opts.get("param_masks", []):
        ok, names, err = read_params(path)
        if not ok:
            steps.append({"file": path, "name": name, "kind": "param",
                          "target": m, "verdict": "read_fail", "note": err})
            break
        hit = [n for n in names if fnmatch.fnmatch(n.upper(), m.upper())]
        steps.append({"file": path, "name": name, "kind": "param", "target": m,
                      "verdict": "delete" if hit else "same",
                      "note": ("найдено: %s" % ", ".join(hit[:20])) if hit
                      else "под маску никто не попал"})
    for old, new in opts.get("rename_map", []):
        ok, names, err = read_features(path, old)
        steps.append({"file": path, "name": name, "kind": "rename",
                      "target": "%s -> %s" % (old, new),
                      "verdict": ("read_fail" if not ok else ("rename" if names else "same")),
                      "note": err if not ok else (("найдено: %s" % ", ".join(names[:20]))
                                                 if names else "элемента нет")})
    return steps


VERDICTS = ("clear", "delete", "rename", "same", "read_fail")
KIND_RU = {"postregen": "постреген.", "param": "параметр", "rename": "переимен."}


def build_plan(root=None, mask="*.asm", limit=MAX_FILES, postregen=True,
               param_masks="", rename_map="", need_stack=True, only=None,
               on_step=None):
    """План по папке. on_step(i, total, имя) - прогресс для окна."""
    opts = {"postregen": bool(postregen),
            "param_masks": parse_masks(param_masks),
            "rename_map": parse_pairs(rename_map)}
    files, err = models_in(root, limit, mask)
    if err:
        return {"error": err}
    if only:
        import fnmatch
        files = [f for f in files
                 if fnmatch.fnmatch(Path(f).name.lower(), only.lower())]
    if not files:
        return {"error": "моделей не найдено под %s по маске %s"
                         % (root or DEFAULT_ROOT, mask)}
    if need_stack:
        ready, why = stack_ready()
        if not ready:
            return {"error": "план построить нечем: %s. Уравнения пост-регенерации "
                             "живут в модели, по файлу не читаются." % why}
    steps = []
    for i, f in enumerate(files, 1):
        if STOP["flag"]:
            break
        if on_step:
            on_step(i, len(files), Path(f).name)
        steps.extend(plan_for_file(f, opts))
    per = {}
    for s in steps:
        per[s["verdict"]] = per.get(s["verdict"], 0) + 1
    will = sum(per.get(v, 0) for v in ("clear", "delete", "rename"))
    # ПРЕДУПРЕЖДЕНИЕ ДО ЗАПИСИ (аудит 04.10.2026): если цель под запрещённым
    # корнем, человек должен увидеть это в плане, а не отказ после согласия.
    root_ok, root_why = write_allowed(root or DEFAULT_ROOT)
    return {"root": str(root or DEFAULT_ROOT), "mask": mask,
            "opts": {"postregen": opts["postregen"],
                     "param_masks": opts["param_masks"],
                     "rename_map": [list(x) for x in opts["rename_map"]]},
            "files": files, "steps": steps, "counts": per,
            "total": len(steps), "will_change": will,
            "write_ok": bool(root_ok), "write_why": root_why,
            "generated": time.strftime("%Y-%m-%d %H:%M:%S")}


VERDICT_RU = {"clear": "очистить", "delete": "удалить", "rename": "переименовать",
              "same": "нечего делать", "read_fail": "не прочитано"}


def write_plan(plan):
    """План на диск: md для человека + JSON для apply.py. Возвращает (md, json).

    План-файл пишется в папку программы log\\postregen_clean, а НЕ в log\\reports:
    там по закону дома лежат только REPORT_<задача>_<исполнитель>_<дата>.md
    (проверка dev\\culture_check.py)."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d_%H%M%S")
    rp = LOG_DIR / ("PLAN_postregen_clean_%s.md" % stamp)
    jp = LOG_DIR / ("plan_postregen_clean_%s.json" % stamp)
    o = plan.get("opts", {})
    shield = ("запись РАЗРЕШЕНА: %s" % plan.get("write_why", "н/д") if plan.get("write_ok")
              else "запись ЗАПРЕЩЕНА щитом: %s" % plan.get("write_why", "н/д"))
    out = ["# ПЛАН ОЧИСТКИ ПОСТ-РЕГЕНЕРАЦИИ (записи ещё НЕ было)", "",
           "Собран: **%s** · корень: `%s` · маска: `%s`" % (
               plan.get("generated"), plan.get("root"), plan.get("mask")), "",
           "- ЩИТ ЗАПИСИ: **%s**" % shield,
           "- уравнения пост-регенерации: **%s**" % ("чистить" if o.get("postregen") else "не трогать"),
           "- маски параметров: **%s**" % (", ".join(o.get("param_masks") or []) or "нет"),
           "- переименования: **%s**" % (
               ", ".join("%s->%s" % tuple(x) for x in (o.get("rename_map") or [])) or "нет"), "",
           "## Сводка", "", "| Что будет | Сколько |", "|---|---|"]
    for v in VERDICTS:
        n = plan.get("counts", {}).get(v, 0)
        if n:
            out.append("| %s | %d |" % (VERDICT_RU[v], n))
    out += ["", "## Шаги (первые 300)", "",
            "| Вид | Модель | Цель | Вердикт | Что найдено |", "|---|---|---|---|---|"]
    for s in plan.get("steps", [])[:300]:
        out.append("| %s | %s | %s | %s | %s |" % (
            KIND_RU.get(s["kind"], s["kind"]), s["name"], s["target"],
            VERDICT_RU.get(s["verdict"], s["verdict"]),
            str(s.get("note", "")).replace("|", "/")[:160]))
    if plan.get("total", 0) > 300:
        out.append("| … ещё %d | | | | |" % (plan["total"] - 300))
    out += ["", "## ЧТО ЭТО НЕ ДЕЛАЕТ",
            "План НИЧЕГО не пишет в модель. Запись — отдельной командой под согласием,",
            "и по умолчанию на копии. Боевые файлы на Z: не трогаются."]
    rp.write_text("\n".join(out), encoding="utf-8")
    jp.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    return str(rp), str(jp)


def main(argv):
    root, mask, only = None, "*.asm", None
    params, rmap, limit, postregen = "", "", MAX_FILES, True
    for a in argv[1:]:
        if a.startswith("--mask="):
            mask = a.split("=", 1)[1]
        elif a.startswith("--only="):
            only = a.split("=", 1)[1]
        elif a.startswith("--param="):
            params = (params + ";" if params else "") + a.split("=", 1)[1]
        elif a.startswith("--rename="):
            rmap = (rmap + ";" if rmap else "") + a.split("=", 1)[1]
        elif a.startswith("--limit="):
            limit = int(a.split("=", 1)[1])
        elif a.startswith("--no-postregen"):
            postregen = False
        elif not a.startswith("-"):
            root = a
    try:
        plan = build_plan(root, mask, limit, postregen, params, rmap, only=only)
    except ValueError as e:
        print("ОШИБКА НАСТРОЕК: %s" % e)
        return 2
    if plan.get("error"):
        print("ОШИБКА ПЛАНА: %s" % plan["error"])
        return 2
    print("ПЛАН ОЧИСТКИ ПОСТ-РЕГЕНЕРАЦИИ (записи ещё нет)")
    print("  корень: %s · маска: %s" % (plan["root"], plan["mask"]))
    print("  моделей: %d · шагов: %d" % (len(plan["files"]), plan["total"]))
    print("  сводка: %s" % plan["counts"])
    print("  изменится: %d" % plan["will_change"])
    rp, jp = write_plan(plan)
    print("-" * 78)
    print("отчёт: %s" % rp)
    print("JSON:   %s" % jp)
    print("ЗАПИСЬ НЕ ВЫПОЛНЯЛАСЬ. Прогон - отдельной командой и только по согласию.")
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv))
def parse_masks(text):
    """'LM_*;MP_*' -> ['LM_*','MP_*']. Это маски имён параметров."""
    return [s.strip() for s in str(text or "").replace(",", ";").split(";") if s.strip()]