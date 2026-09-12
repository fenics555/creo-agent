# -*- coding: utf-8 -*-
r"""
ТРАНСФОРМЕР v12 — ЯДРО (core.py)
Только инфраструктура: пути, лог, трейс, алерты, Ollama, sqlite, текст.
Никакой бизнес-логики.
"""
import json, re, html as H, sqlite3, socket, datetime, urllib.request
from pathlib import Path

BASE = Path(r"D:\AI\tools")
HOST = socket.gethostname().replace(" ", "").replace("-", "")[:16]
DATA_DIR = BASE / "agent" / "data"
DB = DATA_DIR / "agent.sqlite"
CONFIG_FILE = DATA_DIR / "config.json"
ROOTS = BASE / "kb_roots.txt"
if not ROOTS.exists(): ROOTS = BASE / "agent" / "kb_roots.txt"
EXCLUDE_FILE = BASE / "kb_exclude.txt"
if not EXCLUDE_FILE.exists(): EXCLUDE_FILE = BASE / "agent" / "kb_exclude.txt"
LOGF = BASE / ("agent_log_%s.txt" % HOST)
TRACEF = BASE / ("agent_trace_%s.txt" % HOST)
CRASH = BASE / ("crash_%s.txt" % HOST)
REPO = Path(r"D:\AI\repo")
OLL = "http://127.0.0.1:11434"

def log(msg):
    line = "%s %s" % (datetime.datetime.now().strftime("%m-%d %H:%M:%S"), msg)
    try:
        with open(LOGF, "a", encoding="utf-8") as f: f.write(line + "\n")
    except Exception: pass
    print(line)

def log_tail(n=80):
    try:
        with open(LOGF, "r", encoding="utf-8", errors="ignore") as f: return "".join(f.readlines()[-n:])
    except Exception: return "лог пуст"

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
        with open(LOGF, "a", encoding="utf-8") as f: f.write(line + "\n")
    except Exception: pass

def boot_report():
    lines = ["=== старт АГЕНТ v12 на %s ===" % HOST]
    try:
        j = json.load(urllib.request.urlopen(OLL + "/api/tags", timeout=3))
        lines.append("СТАРТ: Ollama=жива, моделей=%d" % len(j.get("models", [])))
    except Exception: lines.append("СТАРТ: Ollama=молчит")
    try:
        r = urllib.request.Request("http://127.0.0.1:8080/creoson",
            json.dumps({"command": "connection", "function": "is_creo_running", "data": {}}).encode(),
            {"Content-Type": "application/json"})
        j = json.load(urllib.request.urlopen(r, timeout=3))
        lines.append("СТАРТ: CREOSON=жив; Creo=%s" % ("запущен" if (j.get("data") or {}).get("running") else "НЕТ"))
    except Exception: lines.append("СТАРТ: CREOSON=молчит")
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