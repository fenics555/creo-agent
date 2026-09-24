# -*- coding: utf-8 -*-
r"""
ТРАНСФОРМЕР v15 — ЯДРО (core.py)
Только инфраструктура: пути, лог, трейс, алерты, Ollama, sqlite, текст.
Никакой бизнес-логики.
"""
import json, re, html as H, sqlite3, socket, datetime, urllib.request
from pathlib import Path

# ==== СКРЫТИЕ КОНСОЛЬНЫХ ОКОН (живая находка 24.09.2026: «моргает синим» — это мелькали окна)
# Агент запускал процессы (скан, индексация, программы, задачи) без CREATE_NO_WINDOW, и на экране
# каждый раз вспыхивал консольный прямоугольник. Патчим subprocess в СВОЁМ процессе: любой запуск
# теперь без окна. GUI-программы (tkinter) свои окна показывают как и раньше — это не консоль.
import subprocess as _sp_mod
if _sp_mod.__name__ == "subprocess" and not getattr(_sp_mod, "_nw_patched", False):
    if hasattr(_sp_mod, "CREATE_NO_WINDOW"):
        _CNW = _sp_mod.CREATE_NO_WINDOW
        _P0, _R0 = _sp_mod.Popen, _sp_mod.run

        def _P_nw(*a, **kw):
            kw.setdefault("creationflags", _CNW)
            return _P0(*a, **kw)

        def _R_nw(*a, **kw):
            kw.setdefault("creationflags", _CNW)
            return _R0(*a, **kw)

        _sp_mod.Popen, _sp_mod.run = _P_nw, _R_nw
        _sp_mod._nw_patched = True


BASE = Path(r"D:\AI\tools")
HOST = socket.gethostname().replace(" ", "").replace("-", "")[:16]
DATA_DIR = BASE / "agent" / "data"
DB = DATA_DIR / "agent.sqlite"
CONFIG_FILE = DATA_DIR / "config.json"
ROOTS = BASE / "kb_roots.txt"
if not ROOTS.exists(): ROOTS = BASE / "agent" / "kb_roots.txt"
EXCLUDE_FILE = BASE / "kb_exclude.txt"
if not EXCLUDE_FILE.exists(): EXCLUDE_FILE = BASE / "agent" / "kb_exclude.txt"
LOGF = Path(r"D:\AI\log\agent") / f"agent_log_{datetime.datetime.now().strftime('%Y-%m-%d')}.txt"
TRACEF = BASE / ("agent_trace_%s.txt" % HOST)
CRASH = BASE / ("crash_%s.txt" % HOST)
REPO = Path(r"D:\AI\repo")
OLL = "http://127.0.0.1:11434"

def log(msg):
    line = "%s %s" % (datetime.datetime.now().strftime("%m-%d %H:%M:%S"), msg)
    try:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
    except Exception: pass
    print(line)

def log_tail(n=80):
    try:
        with open(LOGF, "r", encoding="utf-8", errors="ignore") as f: return "".join(f.readlines()[-n:])
    except Exception: return "лог пуст"

JOBSF = Path(r"D:\AI\log\agent") / "jobs.log"

def job(name, text, **kw):
    """ОБЩИЙ ЖУРНАЛ РАБОТ (решение дома 24.09.2026): каждая программа докладывает о себе в общий
    лог агента — «запущено в фоне», «завершено: файлов=100 обновлено=50». Одинаково работает,
    когда программу запустил человек из своего окна и когда её позвал агент через движок."""
    extra = " ".join("%s=%s" % (k, v) for k, v in kw.items() if v is not None)
    line = "%s РАБОТА %s: %s%s" % (datetime.datetime.now().strftime("%m-%d %H:%M:%S"),
                                   name, text, (" " + extra) if extra else "")
    try:
        JOBSF.parent.mkdir(parents=True, exist_ok=True)
        with open(JOBSF, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    log(line)

def jobs_tail(n=40):
    try:
        with open(JOBSF, "r", encoding="utf-8", errors="ignore") as f:
            return "".join(f.readlines()[-n:])
    except Exception:
        return "журнал работ пуст"

ALERTS = []
def alert(msg, fix=""):
    ALERTS.append({"ts": datetime.datetime.now().strftime("%m-%d %H:%M"), "msg": msg, "fix": fix, "read": False})
    log("УВЕДОМЛЕНИЕ: %s" % msg)
def alerts_get(): return ALERTS
def alerts_mark():
    for a in ALERTS: a["read"] = True

def trace(what, verdict, ms=None, detail=None):
    line = "%s ТРЕЙС %s -> %s" % (datetime.datetime.now().strftime("%m-%d %H:%M:%S"), what, verdict)
    if ms is not None: line += " (%dмс)" % ms
    if detail: line += " | %s" % str(detail)[:120]
    try:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
    except Exception: pass

def boot_report():
    lines = ["=== старт АГЕНТ v12 на %s ===" % HOST]
    try:
        j = json.load(urllib.request.urlopen(OLL + "/api/tags", timeout=3))
        lines.append("СТАРТ: Ollama=жива, моделей=%d" % len(j.get("models", [])))
    except Exception: lines.append("СТАРТ: Ollama=молчит")
    try:
        # 1. Check if CREOSON server is alive with a SAFE command
        r_safe = urllib.request.Request("http://127.0.0.1:8080/creoson",
            json.dumps({"command": "server", "function": "pwd", "data": {}}).encode(),
            {"Content-Type": "application/json"})
        urllib.request.urlopen(r_safe, timeout=3)
        
        # 2. If alive, try the "dangerous" command to check Creo, but handle crash
        try:
            r_creo = urllib.request.Request("http://127.0.0.1:8080/creoson",
                json.dumps({"command": "connection", "function": "is_creo_running", "data": {}}).encode(),
                {"Content-Type": "application/json"})
            j_creo = json.load(urllib.request.urlopen(r_creo, timeout=3))
            creo_status = "запущен" if (j_creo.get("data") or {}).get("running") else "НЕТ"
            lines.append("СТАРТ: CREOSON=жив; Creo=%s" % creo_status)
        except Exception:
            lines.append("СТАРТ: CREOSON=жив; Creo=НЕТ (ошибка проверки)")
    except Exception:
        lines.append("СТАРТ: CREOSON=молчит")
    try:
        c = sqlite3.connect(DB, timeout=10)
        t = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        nf = c.execute("SELECT COUNT(*) FROM files").fetchone()[0] if "files" in t else 0
        nc = c.execute("SELECT COUNT(*) FROM chunks").fetchone()[0] if "chunks" in t else 0
        c.close()
        lines.append("СТАРТ: База=%d файлов, %d чанков" % (nf, nc))
    except Exception: lines.append("СТАРТ: База=недоступна")
    if ROOTS.exists():
        lines.append("СТАРТ: Корни индекса=%d" % sum(1 for l in ROOTS.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")))
    for l in lines: log(l)
    return "\n".join(lines)

def post(u, p, t=600):
    # ОДНА МОДЕЛЬ НА ДОМ: просим Ollama держать веса в памяти (иначе агент и Cline
    # выбивают друг друга и каждая смена = минуты загрузки). Живое решение 24.09.2026.
    if u in ("/api/chat", "/api/generate") and isinstance(p, dict) and "keep_alive" not in p:
        try:
            import settings as _st
            p["keep_alive"] = _st.get("ollama_keep_alive") or "1h"
        except Exception:
            p["keep_alive"] = "1h"
    t0 = datetime.datetime.now().timestamp()
    try:
        r = urllib.request.Request(OLL + u, json.dumps(p).encode(), {"Content-Type": "application/json"})
        j = json.load(urllib.request.urlopen(r, timeout=t))
        trace("OLLAMA %s" % u, "OK", int((datetime.datetime.now().timestamp() - t0) * 1000))
        return j
    except Exception as e:
        trace("OLLAMA %s" % u, "ERR: %s" % str(e)[:60], int((datetime.datetime.now().timestamp() - t0) * 1000))
        raise

def embed(t):
    for _ in range(3):
        try: return post("/api/embeddings", {"model": "nomic-embed-text", "prompt": t, "keep_alive": "30m"}, 120)["embedding"]
        except Exception: import time; time.sleep(2)
    return None

def clean(t):
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", H.unescape(t)).strip()

def chunker(t, size=1500, ov=200):
    s = 0
    while s < len(t):
        yield t[s:s + size]; s += max(1, size - ov)

CREO_EXTS = (".prt", ".asm", ".drw", ".frm", ".sec", ".lay")
def is_creo(fn):
    low = fn.lower()
    return low.endswith(CREO_EXTS) or bool(re.search(r"\.(prt|asm|drw)\.\d+$", low))

def ans(a, srcs=None, verdict="ok"):
    return {"answer": a, "sources": srcs or [], "log_verdict": verdict}

def load_exclude_patterns():
    if not EXCLUDE_FILE.exists(): return []
    return [l.strip() for l in EXCLUDE_FILE.read_text(encoding="utf-8", errors="ignore").splitlines() if l.strip() and not l.startswith("#")]

def is_excluded(path, patterns):
    low = str(path).replace("\\", "/").lower()
    for pat in patterns:
        pp = pat.replace("\\", "/").lower()
        if "*" in pp:
            rx = "^" + re.escape(pp).replace(r"\*", ".*") + "$"
            if re.match(rx, low) or re.match(rx, low.split("/")[-1]): return True
        else:
            if low.endswith("/" + pp) or low.endswith(pp) or ("/" + pp) in low: return True
    return False

def read_roots():
    out = []
    if ROOTS.exists():
        for l in ROOTS.read_text(encoding="utf-8").splitlines():
            l = l.strip()
            if l and not l.startswith("#"): out.append(l)
    return out

def client_id(handler, b=None):
    ip = handler.client_address[0]
    if ip in ("127.0.0.1", "::1"): return "server"
    try: h = socket.gethostbyaddr(ip)[0].split(".")[0]
    except Exception: h = ""
    return h or ip

def db():
    c = sqlite3.connect(DB, timeout=60); c.execute("PRAGMA journal_mode=WAL"); return c

def save_fact(entity_type, entity_name, fact_key, value, source):
    """Сохранить факт в базу данных"""
    try:
        c = db()
        c.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_name TEXT NOT NULL,
                fact_key TEXT NOT NULL,
                value TEXT,
                source TEXT,
                valid_until TEXT
            )
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_facts_entity ON facts(entity_type, entity_name)
        """)
        ts = datetime.datetime.now().isoformat()
        c.execute(
            "INSERT INTO facts (ts, entity_type, entity_name, fact_key, value, source) VALUES (?, ?, ?, ?, ?, ?)",
            (ts, entity_type, entity_name, fact_key, value, source)
        )
        c.commit()
        c.close()
    except Exception as e:
        # В случае ошибки просто пропускаем, чтобы не ломать работу агента
        pass

def get_facts(entity_type=None, entity_name=None, limit=100):
    """Получить факты из базы данных"""
    try:
        c = db()
        query = "SELECT * FROM facts WHERE 1=1"
        params = []
        
        if entity_type is not None:
            query += " AND entity_type = ?"
            params.append(entity_type)
        if entity_name is not None:
            query += " AND entity_name = ?"
            params.append(entity_name)
            
        query += " ORDER BY ts DESC LIMIT ?"
        params.append(limit)
        
        rows = c.execute(query, params).fetchall()
        c.close()
        
        facts = []
        for row in rows:
            facts.append({
                'id': row[0],
                'ts': row[1],
                'entity_type': row[2],
                'entity_name': row[3],
                'fact_key': row[4],
                'value': row[5],
                'source': row[6],
                'valid_until': row[7]
            })
        return facts
    except Exception as e:
        return []

def mark_facts_stale(days_old=30):
    """Пометить старые факты как устаревшие"""
    try:
        c = db()
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_old)
        c.execute(
            "UPDATE facts SET valid_until = ? WHERE ts < ? AND valid_until IS NULL",
            (datetime.datetime.now().isoformat(), cutoff_date.isoformat())
        )
        c.commit()
        c.close()
    except Exception as e:
        # В случае ошибки просто пропускаем
        pass