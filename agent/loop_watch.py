import json, glob, os, time, sys, hashlib, re

SESS = os.path.join(os.path.expanduser("~"), ".cline", "data", "sessions")
ALERT = r"D:\AI\log\urn\cline\LOOP_ALERT.txt"
LOG = os.path.join(os.path.expanduser("~"), ".cline", "data", "logs", "code.log")
THRESHOLD = 2
WINDOW = 12
TXT_WINDOW = 6
TXT_REPEAT = 3
ERR_KEYS = ("error", "not found", "too large", "no replacement",
            "\u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d", "\u043e\u0448\u0438\u0431\u043a")


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


def check():
    s = newest()
    if not s:
        return None
    p = os.path.join(s, os.path.basename(s) + ".messages.json")
    if not os.path.exists(p):
        return None
    try:
        data = json.load(open(p, encoding="utf-8"))
    except Exception:
        return None
    msgs = data.get("messages", [])
    calls = calls_with_results(msgs)[-WINDOW:]
    if len(calls) >= 2:
        err = {}
        for h, rt in calls:
            low = rt.lower()
            if any(k in low for k in ERR_KEYS):
                err[h] = err.get(h, 0) + 1
        for h, c in err.items():
            if c >= THRESHOLD:
                return (os.path.basename(s), c, h, True, "tool-loop")
    tl = text_loop(msgs)
    if tl:
        return (os.path.basename(s), TXT_REPEAT, "TEXT-LOOP", True, "text-loop")
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
        r = check()
        print("ALERT" if (r and r[3]) else "OK", r or "")
        if r and r[3]:
            emit(r)
    else:
        print("watching", SESS, "toolwin", WINDOW, "txtwin", TXT_WINDOW, "txtrepeat", TXT_REPEAT)
        while True:
            r = check()
            if r and r[3]:
                print("\a" + emit(r))
            time.sleep(4)

