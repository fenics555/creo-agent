import json, glob, os, time, sys, hashlib

SESS = os.path.join(os.path.expanduser("~"), ".cline", "data", "sessions")
ALERT = r"D:\AI\log\urn\cline\LOOP_ALERT.txt"
THRESHOLD = 2


def newest():
    ds = glob.glob(os.path.join(SESS, "session_*"))
    return max(ds, key=os.path.getmtime) if ds else None


def tool_calls(msgs):
    calls = []
    for m in msgs:
        if m.get("role") != "assistant":
            continue
        c = m.get("content")
        if isinstance(c, list):
            for b in c:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    key = str(b.get("name", "")) + "|" + json.dumps(b.get("input", {}), sort_keys=True, ensure_ascii=False)
                    calls.append(hashlib.md5(key.encode("utf-8")).hexdigest()[:10])
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
    calls = tool_calls(data["messages"])
    if len(calls) < 2:
        return None
    run = 1
    for i in range(len(calls) - 2, -1, -1):
        if calls[i] == calls[i + 1]:
            run += 1
        else:
            break
    if run >= THRESHOLD:
        return (os.path.basename(s), run, calls[-1])
    return None


if __name__ == "__main__":
    if "--once" in sys.argv:
        r = check()
        print("ALERT" if r else "OK", r or "")
        if r:
            open(ALERT, "a", encoding="utf-8").write("LOOP session=%s repeats=%d call=%s\n" % r)
    else:
        print("watching", SESS, "threshold", THRESHOLD)
        while True:
            r = check()
            if r:
                line = "%s LOOP session=%s repeats=%d call=%s\n" % (time.strftime("%H:%M:%S"), r[0], r[1], r[2])
                open(ALERT, "a", encoding="utf-8").write(line)
                print("\a" + line.strip())
            time.sleep(4)
