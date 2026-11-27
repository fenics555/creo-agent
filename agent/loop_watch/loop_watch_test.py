import json, os, subprocess, sys, shutil, tempfile, time

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


def run(sessdir, log=None, extra=None):
    if log is None:
        log = os.path.join(BASE, "none.log")
    # 26.11.2026: тесты изолируются и от --stats, и от --inbox, иначе фикстуры
    # (tool_loop, faildens, abab...) засоряют боевой stats.json и INBOX.md.
    # 26.11.2026: --no-lock обязателен — иначе тест натыкается на замок живого
    # сторожа («stale lock ... taking over») и падает (2 FAIL из-за гонки).
    cmd = [sys.executable, WATCH, "--once", "--no-lock", "--sess-dir", sessdir,
           "--log", log, "--alert", os.path.join(BASE, "alert.txt"),
           "--stats", os.path.join(BASE, "stats.json"),
           "--inbox", os.path.join(BASE, "inbox.md")]
    if extra:
        cmd += extra
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

big = "\n".join("note: error handling and not found examples in the docs" for _ in range(150))
expect("read_error_words(big) -> OK", run(make("fp_words", [tu("read_files", {"p": "X"}), tr(big),
                                                         tu("read_files", {"p": "X"}), tr(big),
                                                         tu("read_files", {"p": "X"}), tr(big)])), "OK")

ab = [tu("a", {"i": 1}), tr("ok 1"), tu("b", {"i": 2}), tr("ok 2"),
      tu("a", {"i": 1}), tr("ok 3"), tu("b", {"i": 2}), tr("ok 4")]
expect("cycle ABAB(no errors) -> ALERT", run(make("abab", ab)), "ALERT")

es = []
for i in range(3):
    # РЕАЛЬНЫЙ образец (session 1795454643975_b6eh0): результат editor начинается с "Error:"
    es += [tu("editor", {"path": "p", "n": i}), tr("Error: Editor operation failed: file already exists")]
expect("error-sig repeat x3 -> ALERT", run(make("errsig", es)), "ALERT")
es2 = []
for i in range(2):
    es2 += [tu("editor", {"path": "p", "n": i}), tr('{"error":"Editor operation failed: file already exists"}')]
expect("error-sig repeat x2 -> OK", run(make("errsig2", es2)), "OK")

fd = []
# РЕАЛЬНЫЙ образец (замер сессий): провал команды = "[Command exited with code N]" при N != 0.
for i, t in enumerate(["[Command exited with code 1]\nalpha failed",
                       "[Command exited with code 2]\nbeta failed",
                       "[Command exited with code 1]\ngamma failed"]):
    fd += [tu("run_commands", {"cmd": i}), tr(t)]
expect("fail-density x3(diff sigs) -> ALERT", run(make("faildens", fd)), "ALERT")
expect("fail-density x2 -> OK", run(make("faildens2", fd[:4])), "OK")

def age(sessdir, case, secs):
    p = os.path.join(sessdir, case, case + ".messages.json")
    t = time.time() - secs
    os.utime(p, (t, t))


sp = make("spike", [tt("a" * 300)])
expect("spike ON -> ALERT", run(sp, extra=["--spike", "--spike-bytes", "100", "--prev-size", "0"]), "ALERT")
expect("spike OFF -> OK", run(sp), "OK")
expect("spike below -> OK", run(sp, extra=["--spike", "--spike-bytes", "100000000", "--prev-size", "0"]), "OK")

sl = make("stall", [tu("a", {"i": 1}), tr("ok")])
age(sl, "stall", 200)
expect("stall ON(probe yes) -> ALERT", run(sl, extra=["--stall", "--stall-sec", "100", "--probe-reachable", "yes"]), "ALERT")
expect("stall probe no -> OK", run(sl, extra=["--stall", "--stall-sec", "100", "--probe-reachable", "no"]), "OK")
expect("stall OFF -> OK", run(sl), "OK")

sl2 = make("stall_old", [tu("a", {"i": 1}), tr("ok")])
age(sl2, "stall_old", 400)
expect("stall too old -> OK", run(sl2, extra=["--stall", "--stall-sec", "100", "--probe-reachable", "yes"]), "OK")

os.makedirs(os.path.join(BASE, "sess", "empty"), exist_ok=True)
expect("empty -> OK", run(os.path.join(BASE, "sess", "empty")), "OK")

# ── 26.11.2026 (S11): регресс на карту скиллов — через ast (устойчиво к форматированию).
# Было regex `return \([^\n]*?...` — НЕ ловил многострочный return, тест был ФИКТИВНЫМ
# (зелёный на сломанном файле). Урок 273: структурно (AST), не позицией/regex.
import ast as _ast
import glob as _glob
_src = open(WATCH, encoding="utf-8-sig").read()
_tree = _ast.parse(_src)
_map_keys, _map_skills = set(), set()
for _n in _ast.walk(_tree):
    if isinstance(_n, _ast.Assign):
        for _t in _n.targets:
            if isinstance(_t, _ast.Name) and _t.id == "SKILL_MAP" and isinstance(_n.value, _ast.Dict):
                for _k, _v in zip(_n.value.keys, _n.value.values):
                    if isinstance(_k, _ast.Constant) and isinstance(_k.value, str):
                        _map_keys.add(_k.value)
                        if isinstance(_v, _ast.Constant) and isinstance(_v.value, str):
                            _map_skills.add(_v.value)
_kinds = set()
for _n in _ast.walk(_tree):
    if isinstance(_n, _ast.Return) and isinstance(_n.value, _ast.Tuple):
        _e = _n.value.elts
        if len(_e) == 5 and isinstance(_e[-1], _ast.Constant) and isinstance(_e[-1].value, str):
            _kinds.add(_e[-1].value)
        elif len(_e) == 2 and isinstance(_e[0], _ast.Constant) and isinstance(_e[0].value, str):
            _kinds.add(_e[0].value)
_crash_names = {os.path.splitext(os.path.basename(p))[0]
                for p in _glob.glob(r"D:\AI\repo\crash\*.md")}
_bad_kinds = sorted(k for k in _kinds if k not in _map_keys)
_bad_skills = sorted(s for s in _map_skills if s not in _crash_names)
expect("каждый kind имеет ключ в SKILL_MAP (S11, ast)",
       "OK" if not _bad_kinds else str(_bad_kinds), "OK")
expect("SKILL_MAP: все скиллы существуют в crash\\",
       "OK" if not _bad_skills else str(_bad_skills), "OK")

shutil.rmtree(BASE, ignore_errors=True)
print("TOTAL FAIL =", fail)
sys.exit(1 if fail else 0)
