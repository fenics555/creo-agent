# -*- coding: utf-8 -*-
"""QA regression runner for CREO-AGENT. Stdlib only."""
import urllib.request, json, re, time, os, datetime, subprocess, sys, socket

BASE = "http://127.0.0.1:8765"
TOKEN = None
LOG_FILE = r"D:\AI\tools\agent_log_%s.txt" % re.sub(r"[^A-Za-z0-9]", "", socket.gethostname()).lower()


def post(path, data):
    req = urllib.request.Request(
        BASE + path,
        json.dumps(data).encode("utf-8"),
        {"Content-Type": "application/json", "X-Token": TOKEN or ""},
    )
    r = urllib.request.urlopen(req, timeout=180)
    return json.loads(r.read().decode("utf-8"))


def login():
    global TOKEN
    r = post("/login", {"login": "qa_bot_admin", "pw": "QaBot2_2026"})
    if r.get("ok"):
        TOKEN = r.get("token")
        return TOKEN
    post("/register", {"login": "qa_bot_admin", "pw": "QaBot2_2026"})
    r = post("/login", {"login": "qa_bot_admin", "pw": "QaBot2_2026"})
    TOKEN = r.get("token")
    return TOKEN


def ask(q, mode=1):
    return post("/ask", {"token": TOKEN, "q": q, "mode": mode})


def extract_tools(log_lines):
    tools = []
    for l in log_lines:
        m = re.match(r"^\s*([A-Za-z0-9_]+)\(", l)
        if m:
            tools.append(m.group(1))
    return list(dict.fromkeys(tools))


def lat_ratio(text):
    if not text:
        return 0.0
    cleaned = re.sub(r"[A-Za-z]:\\[^ ]+|/[^ ]+|[A-Za-z0-9_-]+\.(?:prt|asm|drw|step)", "", text)
    letters = [c for c in cleaned if c.isalpha()]
    latin = [c for c in letters if c.isascii()]
    return len(latin) / len(letters) if letters else 0.0


def is_pid_running(pid):
    try:
        check = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True)
        return str(pid) in check.stdout
    except Exception:
        return False
