# -*- coding: utf-8 -*-
r"""
АГЕНТ v12 — БЛОК ТРЕЙЛОВ (trail_tools.py)
Семантика (согласована с инженером):
ПАУЗЫ >= 60 сек — ПРОСТОЙ (никто не работал), НЕ болезнь; считаем суммой.
«подавлено N» и регенерации — ИНФО (модель пересохранена из другой), не болезнь.
Болезни: отрицательные/нулевые параметры, @ trail error, hole chart,
translation-файл, медленные открытия (>10 сек), склад версий (>=30), память >150 МБ.
Расчёты траекторий CAM — норма. Накопление: trail_problems (только болезни)
в trail_scans + TRAIL_JOURNAL.md. Разбор: 📐 шаблон + 🧠 мнение ИИ.
machine="" — локальные трейлы; machine="HOST" — центральный трейл машины с шары.
"""
import re, datetime
from pathlib import Path
import core
from core import db
import settings
try:
    import creo_tools as CR
except Exception:
    CR = None

JOURNAL = core.REPO / "Трейлы" / "TRAIL_JOURNAL.md"
FTRAILS = Path(r"Z:\PTC\CREO-START\START-STD\fleet_trails")

_RE_CI = re.compile(r"!%C [IPWE](\d{2}):(\d{2}):(\d{2})\s+(.*)")
_RE_IO = re.compile(r"^!\d{1,2}-[A-Za-z]{3}-\d{2}\s+(\d{2}):(\d{2}):(\d{2})\s+(Start|End)\s+(.+)$")
_RE_MEM = re.compile(r"!mem_use INCREASE. AppSize (\d+)")
_RE_SUPP = re.compile(r"подавлено констр. элементов или компонентов:\s*(\d+)")
_RE_REGEN = re.compile(r"Регенерация\s+(.+?)\s+завершена")
_RE_PARAM = re.compile(r"!%CW\d{2}:\d{2}:\d{2}\s+Параметр '([A-Z_]+)' не может быть отрицательным")
_RE_PECK = re.compile(r"!%CE\d{2}:\d{2}:\d{2}\s+PECK_DEPTH должен быть больше нуля")
_RE_SPIN = re.compile(r"!%CW\d{2}:\d{2}:\d{2}.*?(SPINDLE_SPEED|CLEAR_DIST)")
_RE_TERR = re.compile(r"^@ trail error\s*:\s*(.+)")
_RE_HOLE = re.compile(r"!Error while reading hole chart")
_RE_TRANS = re.compile(r"!Cannot open translation file for configuration dialog")
_RE_VER = re.compile(r"([A-Za-z0-9_\-.]+?\.(?:prt|asm))\.(\d+)$", re.I)

def _init():
    c = db()
    c.execute("""CREATE TABLE IF NOT EXISTS trail_problems(
        id INTEGER PRIMARY KEY AUTOINCREMENT, hash TEXT UNIQUE, kind TEXT,
        subject TEXT, detail TEXT, machine TEXT, first_seen TEXT, last_seen TEXT,
        count INTEGER DEFAULT 1, total_sec REAL DEFAULT 0, status TEXT DEFAULT 'open')""")
    c.execute("""CREATE TABLE IF NOT EXISTS trail_scans(
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, machine TEXT, trail TEXT,
        session TEXT, duration_min INTEGER, mem_peak_mb INTEGER, summary TEXT)""")
    c.commit(); c.close()
_init()

def _upsert(kind, subject, detail, sec=0, machine=""):
    h = "%s|%s" % (kind, subject)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    c = db()
    row = c.execute("SELECT id FROM trail_problems WHERE hash=?", (h,)).fetchone()
    if row:
        c.execute("UPDATE trail_problems SET last_seen=?,count=count+1,total_sec=total_sec+?,status='open' WHERE id=?", (now, sec, row[0]))
    else:
        c.execute("INSERT INTO trail_problems(hash,kind,subject,detail,machine,first_seen,last_seen,count,total_sec) VALUES(?,?,?,?,?,?,?,1,?)", (h, kind, subject, detail, machine, now, now, sec))
    c.commit(); c.close()

def _parse(path):
    lines = Path(path).read_text(encoding="utf-8", errors="ignore").splitlines()
    session = machine = ""
    events, opens, open_times, versions, problems = [], {}, [], {}, []
    carry = prev = 0
    mem_peak = supp_max = regen_cnt = idle = 0
    want_trans = False
    for ln in lines:
        if "Start date" in ln and "time" in ln: session = ln.split(": ", 1)[1].strip()
        if "machine type:" in ln: machine = ln.split(": ", 1)[1].strip()
        m = _RE_MEM.search(ln)
        if m: mem_peak = max(mem_peak, int(m.group(1)))
        m = _RE_SUPP.search(ln)
        if m: supp_max = max(supp_max, int(m.group(1)))
        if _RE_REGEN.search(ln): regen_cnt += 1
        if want_trans:
            want_trans = False
            if ln.startswith("!") and "\\" in ln:
                problems.append(("err_translation", ln.strip("!").split("\\")[-1], "не открывается файл перевода", 0))
        if _RE_TRANS.search(ln): want_trans = True
        if _RE_HOLE.search(ln):
            problems.append(("err_holechart", "hole_charts_thread_series", "ошибка чтения диаграммы отверстий при старте", 0))
        m = _RE_PARAM.search(ln)
        if m: problems.append(("err_param", m.group(1), "отрицательное значение параметра", 0))
        if _RE_PECK.search(ln): problems.append(("err_param", "PECK_DEPTH", "нулевой/отрицательный PECK_DEPTH", 0))
        m = _RE_SPIN.search(ln)
        if m: problems.append(("err_param", m.group(1), "отрицательное значение параметра", 0))
        m = _RE_TERR.match(ln)
        if m:
            mm = re.search(r"in model (\S+)", m.group(1))
            problems.append(("err_feature", mm.group(1) if mm else "feature", m.group(1)[:80], 0))
        m = _RE_IO.match(ln)
        if m:
            sec = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
            p = m.group(5).strip()
            bv = _RE_VER.search(p)
            if bv: versions[bv.group(1)] = max(versions.get(bv.group(1), 0), int(bv.group(2)))
            if m.group(4) == "Start": opens[p] = sec
            elif p in opens: open_times.append((sec - opens[p], p))
            continue
        m = _RE_CI.match(ln)
        if m:
            sec = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
            if prev and sec < prev - 3600: carry += 86400
            prev = sec
            events.append((sec + carry, m.group(4)))
    for i in range(1, len(events)):
        d = events[i][0] - events[i - 1][0]
        if d >= 60: idle += d
    for d, pth in open_times:
        if d > 10: problems.append(("open_slow", Path(pth).name[:60], "открытие %d сек" % d, d))
    for base, ver in versions.items():
        if ver >= 30: problems.append(("versions_pile", base, "склад версий .%d — пора чистить" % ver, 0))
    if mem_peak > 150000000:
        problems.append(("mem_high", session[:10], "пик памяти %d МБ" % (mem_peak // 1000000), 0))
    duration = (events[-1][0] - events[0][0]) if events else 0
    return {"file": str(path), "session": session, "machine": machine,
            "duration_min": duration // 60, "idle_min": idle // 60,
            "mem_peak_mb": mem_peak // 1000000, "supp_max": supp_max,
            "regen_cnt": regen_cnt, "problems": problems, "opens": len(open_times)}

_NAMES = {"err_param": "ОШИБКИ ПАРАМЕТРОВ", "err_feature": "ОШИБКИ FEATURE",
          "err_holechart": "ДИАГРАММА ОТВЕРСТИЙ", "err_translation": "ПЕРЕВОД",
          "versions_pile": "СКЛАД ВЕРСИЙ", "open_slow": "МЕДЛЕННЫЕ ОТКРЫТИЯ", "mem_high": "ПАМЯТЬ"}

def _report(r):
    out = ["=== %s ===" % Path(r["file"]).name,
           "сессия: %s | ~%d мин | простой ~%d мин (никто не работал) | память %d МБ"
           % (r["session"], r["duration_min"], r["idle_min"], r["mem_peak_mb"]),
           "регенераций: %d, подавлено макс: %d (инфо, не болезнь)" % (r["regen_cnt"], r["supp_max"])]
    kinds = {}
    for kind, subj, det, sec in r["problems"]: kinds.setdefault(kind, []).append((subj, det))
    for k, items in kinds.items():
        out.append("%s (%d):" % (_NAMES.get(k, k), len(items)))
        for subj, det in items[:5]: out.append("  • %s — %s" % (subj, det))
    if not r["problems"]: out.append("болезней не найдено")
    return "\n".join(out)

def _store(r):
    for kind, subj, det, sec in r["problems"]:
        _upsert(kind, subj, det, sec, r["machine"])
    c = db()
    c.execute("INSERT INTO trail_scans(ts,machine,trail,session,duration_min,mem_peak_mb,summary) VALUES(?,?,?,?,?,?,?)",
              (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), r["machine"], Path(r["file"]).name,
               r["session"], r["duration_min"], r["mem_peak_mb"],
               "; ".join("%s:%s" % (k, s) for k, s, _, _ in r["problems"][:8])))
    c.commit(); c.close()

def _journal(reps):
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    sec = ["", "## %s | %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                               ", ".join(Path(r["file"]).name for r in reps))]
    for r in reps:
        sec.append("- %s: сессия %s (~%d мин), простой ~%d мин, память %d МБ"
                   % (Path(r["file"]).name, r["session"], r["duration_min"], r["idle_min"], r["mem_peak_mb"]))
        for kind, subj, det, s in r["problems"][:10]: sec.append("  • [%s] %s — %s" % (kind, subj, det))
    body = "\n".join(sec) + "\n"
    if JOURNAL.exists(): JOURNAL.write_text(JOURNAL.read_text(encoding="utf-8") + body, encoding="utf-8")
    else: JOURNAL.write_text("# ЖУРНАЛ ТРЕЙЛОВ (накопительный)\n" + body, encoding="utf-8")

def _find_trails(count):
    dirs = []
    if CR:
        v = ((CR.creo_call("creo", "get_config", {"name": "trail_dir"}, 10) or {}).get("data") or {}).get("values") or []
        if v: dirs.append(v[0])
    dirs += [r"D:\PTC\CREO-LOCAL-SETUP\TEMP\trails", r"D:\PTC"]
    files = []
    for d in dirs:
        try: files += list(Path(d).glob("trail.txt.*"))
        except Exception: pass
    files = sorted(set(files), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:max(1, min(int(count or 1), 5))]

def _scan(count, machine=""):
    if machine:
        host = machine.strip().upper()
        files = sorted(FTRAILS.glob("%s__trail.txt.*" % host), key=lambda p: p.stat().st_mtime) if FTRAILS.exists() else []
        if not files: return []
        r = _parse(files[-1]); r["machine"] = host
        _store(r)
        return [r]
    reps = []
    for f in _find_trails(count):
        r = _parse(f)
        _store(r)
        reps.append(r)
    if reps: _journal(reps)
    return reps

def tool_trail_analyze(count=1, machine="", **kw):
    reps = _scan(count, machine)
    if not reps:
        return ("нет центрального трейла машины %s (машина ещё не запускалась с новым CREO-START)" % machine) if machine else "трейлы не найдены (проверь trail_dir)"
    return "\n\n".join(_report(r) for r in reps)

def _llm_opinion(facts):
    prompt = ("Ты — инженер-диагност Creo Parametric. Думай и отвечай ТОЛЬКО на русском языке.\n"
              "Факты из трейлов:\n%s\nКоротко (до 10 строк): главные причины тормозов/ошибок и что делать инженеру." % facts)
    try:
        r = core.post("/api/chat", {"model": settings.model_for("trail") or "deepseek-r1:14b", "stream": False,
                                    "options": {"temperature": 0.2, "num_predict": 1024},
                                    "messages": [{"role": "user", "content": prompt}]}, t=300)
        return re.sub(r"<think>[\s\S]*?</think>", "", r["message"]["content"]).strip() or "(мнения нет)"
    except Exception as e:
        return "(ИИ не ответил: %s)" % e

def tool_trail_diagnose(count=1, machine="", **kw):
    reps = _scan(count, machine)
    if not reps:
        return ("нет центрального трейла машины %s" % machine) if machine else "трейлы не найдены"
    facts = "\n\n".join(_report(r) for r in reps)
    return "📐 ПО ШАБЛОНУ:\n%s\n\n🧠 МНЕНИЕ ИИ:\n%s" % (facts, _llm_opinion(facts))

def tool_trail_problems(status="open", **kw):
    c = db()
    q = "SELECT kind,subject,count,first_seen,last_seen,total_sec,status FROM trail_problems"
    if status in ("open", "closed"): q += " WHERE status='%s'" % status
    q += " ORDER BY count DESC"
    rows = c.execute(q).fetchall(); c.close()
    if not rows: return "накопленных болезней нет"
    out = ["НАКОПЛЕННЫЕ БОЛЕЗНИ ТРЕЙЛОВ:"]
    for kind, subj, cnt, fs, ls, tsec, st in rows:
        out.append("• [%s] %s — %s — %d раз (первый %s, последний %s, сумма %.0f сек)" % (_NAMES.get(kind, kind), subj, st, cnt, fs, ls, tsec or 0))
    return "\n".join(out)

def tool_trail_trend(**kw):
    c = db()
    rows = c.execute("SELECT kind,subject,SUM(total_sec),SUM(count) FROM trail_problems GROUP BY kind,subject ORDER BY SUM(total_sec) DESC").fetchall()
    c.close()
    if not rows: return "нет данных для тренда"
    out = ["ТРЕНД ПОТЕРЬ ВРЕМЕНИ:"]
    for kind, subj, tsec, cnt in rows:
        out.append("• %s / %s — %.0f сек (%.1f мин) за %d случаев" % (_NAMES.get(kind, kind), subj, tsec or 0, (tsec or 0) / 60, cnt))
    return "\n".join(out)

TOOLS = [
    {"name": "trail_analyze", "desc": "Разбор трейлов Creo: простой, регенерации (инфо), болезни. machine пусто = локально, имя хоста = центральная копия с шары", "params": {"count": "сколько последних трейлов (1)", "machine": "имя хоста (пусто = локально)"}, "approval": False, "fn": tool_trail_analyze},
    {"name": "trail_diagnose", "desc": "Факты по шаблону + мнение ИИ на русском; machine — как в trail_analyze", "params": {"count": "сколько трейлов (1)", "machine": "имя хоста (пусто = локально)"}, "approval": False, "fn": tool_trail_diagnose},
    {"name": "trail_problems", "desc": "Накопленные болезни трейлов со счётчиками повторений", "params": {"status": "open/closed/all"}, "approval": False, "fn": tool_trail_problems},
    {"name": "trail_trend", "desc": "Тренд потерь времени: сколько секунд съела каждая болезнь", "params": {}, "approval": False, "fn": tool_trail_trend},
]