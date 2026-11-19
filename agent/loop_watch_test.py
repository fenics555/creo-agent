import json, os, subprocess, sys, shutil, tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
WATCH = os.path.join(ROOT, "loop_watch.py")
BASE = tempfile.mkdtemp(prefix="loop_watch_test_")


def w(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def tu(name, inp):
    return {"role": "assistant", "content": [{"type": "tool_use", "name": name, "input": inp}]}


def tr(text, query=""):
    return {"role": "user", "content": [{"type": "tool_result", "content": [{"result": text, "query": query}]}]}


def tt(text):
    return {"role": "assistant", "content": [{"type": "text", "text": text}]}


def make(case, msgs):
    d = os.path.join(BASE, "sess", case, case)
    w(os.path.join(d, case + ".messages.json"), {"messages": msgs})
    return os.path.join(BASE, "sess", case)


def run(sessdir, log=None):
    if log is None:
        log = os.path.join(BASE, "none.log")
    cmd = [sys.executable, WATCH, "--once", "--sess-dir", sessdir,
           "--log", log, "--alert", os.path.join(BASE, "alert.txt")]
    out = subprocess.run(cmd, capture_output=True, text=True)
    return (out.stdout or "").strip()


fail = 0


def expect(label, got, want):
    global fail
    ok = got.startswith(want)
    if not ok:
        fail += 1
    print(("PASS " if ok else "FAIL ") + label + " | got=" + got[:70])


sd = make("tool_loop", [tu("read_files", {"a": 1}), tr("error: not found"),
                        tu("read_files", {"a": 1}), tr("error: not found")])
expect("tool_loop -> ALERT", run(sd), "ALERT")

msgs = [tu("read_files", {"a": 2}), tr("error: not found"),
        tu("read_files", {"a": 2}), tr("error: not found")]
for i in range(13):
    msgs += [tu("read_files", {"b": i}), tr("ok result %d" % i)]
expect("old_loop(outside window) -> OK", run(make("old_loop", msgs)), "OK")

expect("single_err -> OK", run(make("single_err", [tu("x", {"a": 1}), tr("error"),
                                                   tu("y", {"a": 2}), tr("ok")])), "OK")

T = "I will now continue examining the very same situation repeatedly without any progress"
expect("text_loop -> ALERT", run(make("text_loop", [tt(T), tt(T), tt(T)])), "ALERT")
expect("text_twice -> OK", run(make("text_twice", [tt(T), tt(T)])), "OK")

expect("clean -> OK", run(make("clean", [tu("a", {"i": 1}), tr("ok 1"),
                                         tu("b", {"i": 2}), tr("ok 2"),
                                         tt("distinct one here"), tt("distinct two here")])), "OK")

sd = make("aborted", [tu("a", {"i": 1}), tr("ok")])
lg = os.path.join(BASE, "aborted.log")
open(lg, "w", encoding="utf-8").write(
    'x "Desktop chat prompt completed" session aborted id="aborted" "finishReason":"aborted"\n')
expect("aborted log -> ALERT", run(sd, lg), "ALERT")

os.makedirs(os.path.join(BASE, "sess", "empty"), exist_ok=True)
expect("empty -> OK", run(os.path.join(BASE, "sess", "empty")), "OK")

shutil.rmtree(BASE, ignore_errors=True)
print("TOTAL FAIL =", fail)
sys.exit(1 if fail else 0)
