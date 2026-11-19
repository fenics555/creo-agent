import json, glob, os, time, sys, hashlib, re, urllib.request, urllib.error

SESS = os.path.join(os.path.expanduser("~"), ".cline", "data", "sessions")
ALERT = r"D:\AI\log\urn\cline\LOOP_ALERT.txt"
LOG = os.path.join(os.path.expanduser("~"), ".cline", "data", "logs", "code.log")
THRESHOLD = 2
WINDOW = 12
TXT_WINDOW = 6
TXT_REPEAT = 3
CYCLE_PAIRS = 2
ERR_MAX_LEN = 4000
COOLDOWN_SEC = 20
ERR_KEYS = ("error", "not found", "too large", "no replacement",
            "\u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d", "\u043e\u0448\u0438\u0431\u043a")
BACKEND_PROBES = (
    ("llama.cpp", "http://127.0.0.1:8080/health", "health"),
    ("vllm", "http://127.0.0.1:8000/health", "health"),
    ("vllm_stall", "http://127.0.0.1:8000/health/decode", "stall"),
    ("ollama", "http://127.0.0.1:11434/api/ps", "ps"),
    ("lmstudio", "http://127.0.0.1:1234/v1/models", "health"),
    ("textgen", "http://127.0.0.1:5000/v1/models", "health"),
)
POLL_SEC = 4
STALL_SEC = 110
RECENT_SEC = 300
SPIKE_BYTES = 65536
PROBE_TIMEOUT = 1.5


def arg(name, default=None):
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


SESSION_ID = arg("--session")
SESS = arg("--sess-dir", SESS)
LOG = arg("--log", LOG)
ALERT = arg("--alert", ALERT)
WINDOW = int(arg("--window", WINDOW))
TXT_WINDOW = int(arg("--txt-window", TXT_WINDOW))
TXT_REPEAT = int(arg("--txt-repeat", TXT_REPEAT))
STALL_ENABLED = "--stall" in sys.argv
SPIKE_ENABLED = "--spike" in sys.argv
STALL_SEC = int(arg("--stall-sec", STALL_SEC))
RECENT_SEC = int(arg("--recent-sec", RECENT_SEC))
SPIKE_BYTES = int(arg("--spike-bytes", SPIKE_BYTES))
PREV_SIZE = arg("--prev-size")
PROBE_REACHABLE = arg("--probe-reachable")
PROBE_TIMEOUT = float(arg("--probe-timeout", PROBE_TIMEOUT))


def newest():
    if SESSION_ID:
        d = os.path.join(SESS, SESSION_ID)
        return d if os.path.isdir(d) else None
    ds = [d for d in glob.glob(os.path.join(SESS, "*"))
          if os.path.isdir(d) and "__agent_" not in os.path.basename(d)]
    return max(ds, key=os.path.getmtime) if ds else None


def calls_with_results(msgs):
    calls = []
    pending = None
    for m in msgs:
        role = m.get("role")
        c = m.get("content")
        if role == "assistant" and isinstance(c, list):
            for b in c:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    key = str(b.get("name", "")) + "|" + json.dumps(b.get("input", {}), sort_keys=True, ensure_ascii=False)
                    pending = hashlib.md5(key.encode("utf-8")).hexdigest()[:10]
        elif role == "user" and isinstance(c, list):
            rt = ""
            for b in c:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    rc = b.get("content")
                    if isinstance(rc, list):
                        rt = " ".join(str(x.get("result", "")) + " " + str(x.get("query", "")) for x in rc if isinstance(x, dict))
                    else:
                        rt = str(rc)
            if pending is not None:
                calls.append((pending, rt))
                pending = None
    return calls


def assistant_texts(msgs):
    texts = []
    for m in msgs:
        if m.get("role") != "assistant":
            continue
        c = m.get("content")
        if isinstance(c, list):
            t = " ".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
        elif isinstance(c, str):
            t = c
        else:
            t = ""
        t = re.sub(r"\s+", " ", t).strip()
        if t:
            texts.append(t)
    return texts


def norm(t):
    return re.sub(r"[^0-9a-z\u0400-\u04ff]+", " ", t.lower()).strip()


def is_error_result(rt):
    if len(rt) > ERR_MAX_LEN:
        return False
    low = rt.lower()
    return any(k in low for k in ERR_KEYS)


def cycle_loop(calls):
    sigs = [h for h, _ in calls]
    n = CYCLE_PAIRS * 2
    if len(sigs) < n:
        return None
    tail = sigs[-n:]
    if tail[0] != tail[1] and tail == [tail[0], tail[1]] * CYCLE_PAIRS:
        return "%s<->%s" % (tail[0], tail[1])
    return None


def session_messages_path(s):
    p = os.path.join(s, os.path.basename(s) + ".messages.json")
    if os.path.exists(p):
        return p
    meta = os.path.join(s, os.path.basename(s) + ".json")
    try:
        d = json.load(open(meta, encoding="utf-8"))
        mp = d.get("messages_path")
        if mp:
            if not os.path.isabs(mp):
                mp = os.path.join(s, mp)
            if os.path.exists(mp):
                return mp
    except Exception:
        pass
    return None


def _http_get(url):
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=PROBE_TIMEOUT) as r:
            return r.status, r.read(256)
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception:
        return None, b""


def probe_backends():
    if PROBE_REACHABLE == "yes":
        return {"alive": True, "stall": False, "active_model": "forced", "hits": []}
    if PROBE_REACHABLE == "no":
        return {"alive": False, "stall": False, "active_model": None, "hits": []}
    res = {"alive": False, "stall": False, "active_model": None, "hits": []}
    for name, url, kind in BACKEND_PROBES:
        status, body = _http_get(url)
        if status is None:
            continue
        res["alive"] = True
        res["hits"].append((name, kind, status))
        if kind == "stall" and status == 503:
            res["stall"] = True
        elif kind == "ps":
            try:
                data = json.loads(body.decode("utf-8", errors="replace"))
                models = data.get("models") or []
                if models:
                    res["active_model"] = models[0].get("name") or models[0].get("model")
            except Exception:
                pass
    return res


def text_loop(msgs):
    texts = assistant_texts(msgs)[-TXT_WINDOW:]
    norms = [n for n in (norm(t) for t in texts) if len(n) >= 20]
    if len(norms) < TXT_REPEAT:
        return None
    counts = {}
    for n in norms:
        counts[n] = counts.get(n, 0) + 1
    n, c = max(counts.items(), key=lambda kv: kv[1])
    if c >= TXT_REPEAT:
        return texts[-1][:60]
    return None


def check_log(session_id):
    if not os.path.exists(LOG):
        return None
    try:
        lines = open(LOG, encoding="utf-8", errors="replace").read().splitlines()[-5000:]
    except Exception:
        return None
    last = None
    for ln in lines:
        if "Desktop chat prompt completed" in ln and session_id in ln:
            last = ln
    if last and '"finishReason":"aborted"' in last:
        return True
    return None


def check(prev_size=None):
    s = newest()
    if not s:
        return None
    p = session_messages_path(s)
    if not p:
        return None
    if SPIKE_ENABLED and prev_size is not None:
        size = os.path.getsize(p)
        if size - prev_size >= SPIKE_BYTES:
            return (os.path.basename(s), size - prev_size, "SPIKE", True, "context-spike")
    try:
        data = json.load(open(p, encoding="utf-8"))
    except Exception:
        return None
    msgs = data.get("messages", [])
    calls = calls_with_results(msgs)[-WINDOW:]
    if len(calls) >= 2:
        err = {}
        for h, rt in calls:
            if is_error_result(rt):
                err[h] = err.get(h, 0) + 1
        for h, c in err.items():
            if c >= THRESHOLD:
                return (os.path.basename(s), c, h, True, "tool-loop")
    cyc = cycle_loop(calls)
    if cyc:
        return (os.path.basename(s), CYCLE_PAIRS * 2, "CYCLE", True, "cycle-loop")
    tl = text_loop(msgs)
    if tl:
        return (os.path.basename(s), TXT_REPEAT, "TEXT-LOOP", True, "text-loop")
    if STALL_ENABLED:
        idle = time.time() - os.path.getmtime(p)
        if STALL_SEC <= idle < RECENT_SEC:
            pr = probe_backends()
            if pr["alive"] or pr["stall"]:
                return (os.path.basename(s), int(idle), "STALL:" + str(pr["active_model"] or "backend"), True, "generation-stall")
    if check_log(os.path.basename(s)):
        return (os.path.basename(s), 0, "ABORTED", True, "aborted")
    return None


def emit(r):
    line = "%s LOOP kind=%s session=%s repeats=%d call=%s\n" % (
        time.strftime("%H:%M:%S"), r[4], r[0], r[1], r[2])
    try:
        open(ALERT, "a", encoding="utf-8").write(line)
    except Exception:
        pass
    return line.strip()


if __name__ == "__main__":
    if "--once" in sys.argv:
        prev = int(PREV_SIZE) if PREV_SIZE is not None else None
        r = check(prev_size=prev)
        print("ALERT" if (r and r[3]) else "OK", r or "")
        if r and r[3]:
            emit(r)
    else:
        print("watching", SESS, "toolwin", WINDOW, "txtwin", TXT_WINDOW, "txtrepeat", TXT_REPEAT,
              "stall", STALL_ENABLED, "spike", SPIKE_ENABLED)
        last = {"sig": None, "ts": 0.0, "size": {}}
        while True:
            s = newest()
            name = os.path.basename(s) if s else ""
            r = check(prev_size=last["size"].get(name))
            if r and r[3]:
                sig = "%s|%s|%s" % (r[4], r[0], r[2])
                now = time.time()
                if not (sig == last["sig"] and now - last["ts"] < COOLDOWN_SEC):
                    last["sig"] = sig
                    last["ts"] = now
                    print("\a" + emit(r))
            p = session_messages_path(s) if s else None
            if p:
                last["size"][name] = os.path.getsize(p)
            time.sleep(POLL_SEC)

