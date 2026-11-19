import json, glob, os, time, sys, hashlib

SESS = os.path.join(os.path.expanduser("~"), ".cline", "data", "sessions")
ALERT = r"D:\AI\log\urn\cline\LOOP_ALERT.txt"
THRESHOLD = 2


SESSION_ID = None
if "--session" in sys.argv:
    SESSION_ID = sys.argv[sys.argv.index("--session") + 1]


def newest():
    if SESSION_ID:
        d = os.path.join(SESS, SESSION_ID)
        return d if os.path.isdir(d) else None
    ds = glob.glob(os.path.join(SESS, "session_*"))
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
    calls = calls_with_results(data["messages"])
    if len(calls) < 2:
        return None
    run = 1
    for i in range(len(calls) - 2, -1, -1):
        if calls[i][0] == calls[i + 1][0]:
            run += 1
        else:
            break
    if run < THRESHOLD:
        return None
    tail = calls[-run:]
    low = " ".join(r[1].lower() for r in tail)
    err = any(k in low for k in ("error", "not found", "too large", "не найден", "ошибк"))
    return (os.path.basename(s), run, calls[-1][0], err)


if __name__ == "__main__":
    if "--once" in sys.argv:
        r = check()
        print("ALERT" if (r and r[3]) else "OK", r or "")
        if r and r[3]:
            open(ALERT, "a", encoding="utf-8").write("LOOP session=%s repeats=%d call=%s\n" % (r[0], r[1], r[2]))
    else:
        print("watching", SESS, "threshold", THRESHOLD, "(alert only on repeat-after-error)")
        while True:
            r = check()
            if r and r[3]:
                line = "%s LOOP session=%s repeats=%d call=%s\n" % (time.strftime("%H:%M:%S"), r[0], r[1], r[2])
                open(ALERT, "a", encoding="utf-8").write(line)
                print("\a" + line.strip())
            time.sleep(4)
