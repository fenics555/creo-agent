import json, os, sys

SESS = os.path.join(os.path.expanduser("~"), ".cline", "data", "sessions")


def arg(name, default=None):
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


SESS = arg("--sess-dir", SESS)


def calls(msgs):
    uses = []
    results = {}
    for i, m in enumerate(msgs):
        c = m.get("content")
        if not isinstance(c, list):
            continue
        for b in c:
            if not isinstance(b, dict):
                continue
            t = b.get("type")
            if t == "tool_use":
                uses.append((i, b.get("id"), str(b.get("name", "")), json.dumps(b.get("input", {}), ensure_ascii=False)))
            elif t == "tool_result":
                rc = b.get("content")
                txt = json.dumps(rc, ensure_ascii=False) if not isinstance(rc, str) else rc
                tid = b.get("tool_use_id") or b.get("toolUseId")
                results[tid] = txt
    return [(i, name, s, results.get(uid, "")) for (i, uid, name, s) in uses]


def check(msgs):
    cs = calls(msgs)
    v = {
        "R1_powershell_Command": [i for (i, nm, s, r) in cs if nm == "run_commands" and "powershell" in s and "-Command" in s],
        "R2_read_truncated": [i for (i, nm, s, r) in cs if nm == "read_files" and "truncated" in r],
        "R3_editor_already_exists": [i for (i, nm, s, r) in cs if nm == "editor" and "already exists" in r],
        "R4_recursive_scan": [i for (i, nm, s, r) in cs if nm == "run_commands" and "-Recurse" in s and "-Depth" not in s],
    }
    return cs, v


def load(sid):
    p = os.path.join(SESS, sid, sid + ".messages.json")
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("messages", [])


if __name__ == "__main__":
    sid = sys.argv[1]
    msgs = load(sid)
    cs, v = check(msgs)
    print("SESSION", sid, "tool_calls", len(cs))
    total = 0
    for k in sorted(v):
        n = len(v[k])
        total += n
        print("  %-26s %3d  %s" % (k, n, "VIOLATION" if n else "ok"))
        if n:
            print("      idx=" + ",".join(str(x) for x in v[k][:20]))
    print("TOTAL_VIOLATIONS", total)
    sys.exit(1 if total else 0)
