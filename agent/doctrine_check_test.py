import json, os, subprocess, sys, shutil, tempfile, hashlib

ROOT = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(ROOT, "doctrine_check.py")
REPO = r"D:\AI\repo"
CL_ROOT = r"D:\AI\.clinerules"
CL_REPO = os.path.join(REPO, ".clinerules")
BASE = tempfile.mkdtemp(prefix="doctrine_test_")
fail = 0


def w(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


_n = [0]


def tu(name, inp):
    _n[0] += 1
    return {"role": "assistant", "content": [{"type": "tool_use", "id": "c%d" % _n[0], "name": name, "input": inp}]}


def tr(text):
    return {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "c%d" % _n[0], "content": [{"result": text, "query": ""}]}]}


def make(case, msgs):
    d = os.path.join(BASE, case, case)
    w(os.path.join(d, case + ".messages.json"), {"messages": msgs})
    return os.path.join(BASE, case), case


def run_check(sessdir, case):
    cmd = [sys.executable, CHECK, case, "--sess-dir", sessdir]
    out = subprocess.run(cmd, capture_output=True, text=True)
    return (out.stdout or "")


def expect(label, cond):
    global fail
    if not cond:
        fail += 1
    print(("PASS " if cond else "FAIL ") + label)


# --- behavioral fixtures ---
bad = [tu("run_commands", {"commands": ["powershell.exe -Command \"$x = 'Z:\\...'; Write-Host $x\""]}), tr("The term '=' is not recognized"),
       tu("run_commands", {"commands": ["Get-ChildItem 'D:\\AI' -Recurse"]}), tr("ok"),
       tu("read_files", {"files": [{"path": "big"}]}), tr("line1 ... [truncated"),
       tu("editor", {"path": "p", "new_text": "x"}), tr("Editor operation failed: p already exists")]
sd, case = make("bad", bad)
o = run_check(sd, case)
expect("bad session flagged (TOTAL_VIOLATIONS >= 4)", "TOTAL_VIOLATIONS 4" in o or "TOTAL_VIOLATIONS 5" in o)
expect("bad R1 powershell -Command detected", "R1_powershell_Command" in o and "VIOLATION" in o)

good = [tu("run_commands", {"commands": ["(Get-Item -LiteralPath 'D:\\AI\\repo\\SKILL_recon.md').Length", "(Get-Content 'D:\\AI\\repo\\SKILL_recon.md').Count"]}), tr("5399\n46"),
        tu("run_commands", {"commands": ["Select-String -Path 'D:\\AI\\repo\\SKILL_recon.md' -Pattern 'ВИЛКА'"]}), tr("L20: ..."),
        tu("read_files", {"path": "D:\\AI\\repo\\SKILL_recon.md", "start_line": 18, "end_line": 24}), tr("1 | ...") ,
        tu("editor", {"path": "p", "old_text": "unique line", "new_text": "new"}), tr("Edited p")]
sd, case = make("good", good)
o = run_check(sd, case)
expect("good session clean (TOTAL_VIOLATIONS 0)", "TOTAL_VIOLATIONS 0" in o)

# --- structural wiring ---
expect("SKILL_recon.md exists", os.path.exists(os.path.join(REPO, "SKILL_recon.md")))
recon = open(os.path.join(REPO, "SKILL_recon.md"), encoding="utf-8").read()
expect("recon has ВИЛКА", "ВИЛКА" in recon)
cl = open(CL_ROOT, encoding="utf-8").read()
expect("clinerules strong mandate", "РАЗВЕДКА ОБЯЗАТЕЛЬНА" in cl)
expect("clinerules trigger SKILL_recon.md", "SKILL_recon.md" in cl)
h1 = hashlib.sha256(open(CL_ROOT, "rb").read()).hexdigest()
h2 = hashlib.sha256(open(CL_REPO, "rb").read()).hexdigest()
expect("clinerules copies synced", h1 == h2)
eg = open(os.path.join(REPO, "SKILL_edit_gotchas.md"), encoding="utf-8").read()
expect("edit_gotchas has S0 route", "МАРШРУТ ПЕРЕД ПРАВКОЙ" in eg)
expect("edit_gotchas has loop signature", "not recognized as the name of a cmdlet" in eg)
idx = open(os.path.join(REPO, "SKILL_index.md"), encoding="utf-8").read()
expect("index routes recon", "SKILL_recon.md" in idx)

# --- live: test on myself + on the looping gemma session ---
for lbl, sid in [("MYSELF", "1795113666869_yfc0g"), ("GEMMA", "session_1795116869320_lsqj5")]:
    try:
        o = run_check(os.path.join(os.path.expanduser("~"), ".cline", "data", "sessions"), sid)
        line = [x for x in o.splitlines() if x.startswith("TOTAL_VIOLATIONS")]
        print("LIVE %s: %s" % (lbl, line[0] if line else "n/a"))
    except Exception as e:
        print("LIVE %s: err %s" % (lbl, e))

shutil.rmtree(BASE, ignore_errors=True)
print("TOTAL FAIL =", fail)
sys.exit(1 if fail else 0)
