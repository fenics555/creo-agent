import json, os, subprocess, sys, tempfile, shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import rule_variant_test as rv

DC = os.path.join(ROOT, "doctrine_check.py")

COVER = {
    "R1_powershell_Command": ["-Command", "powershell", ".ps1", "-File"],
    "R2_read_truncated": ["Get-Item", "байт", "строк", "диапазон", "Length"],
    "R3_editor_already_exists": ["old_text", "SKILL_edit_gotchas", "якор"],
    "R4_recursive_scan": ["-Recurse", "рекурс", "глубин", "-Depth"],
    "R5_getcontent_no_encoding": ["-Encoding"],
}


def covers(t):
    low = t.lower()
    return {k for k, ws in COVER.items() if any(w.lower() in low for w in ws)}


def tu(name, inp, i):
    return {"role": "assistant", "content": [{"type": "tool_use", "id": "c%d" % i, "name": name, "input": inp}]}


def tr(text, i):
    return {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "c%d" % i, "content": [{"result": text, "query": ""}]}]}


def sess_following(cov):
    """Сессия 'модель следует варианту': что вариант покрывает — делаем правильно; чего нет — как обычно (спотыкание)."""
    m = []
    i = [0]

    def add(name, inp, res):
        i[0] += 1
        m.append(tu(name, inp, i[0]))
        m.append(tr(res, i[0]))

    if "R2_read_truncated" in cov:
        add("run_commands", {"commands": ["(Get-Item 'big').Length"]}, "60000")
        add("read_files", {"path": "big", "start_line": 1, "end_line": 20}, "1 | ok")
    else:
        add("read_files", {"path": "big"}, "line ... [truncated")

    if "R4_recursive_scan" in cov:
        add("run_commands", {"commands": ["(Get-ChildItem 'd').Count"]}, "5")
    else:
        add("run_commands", {"commands": ["Get-ChildItem 'd' -Recurse"]}, "many")

    if "R3_editor_already_exists" in cov:
        add("editor", {"path": "x", "old_text": "a", "new_text": "b"}, "Edited x")
    else:
        add("editor", {"path": "x", "new_text": "b"}, "Editor operation failed: x already exists")

    if "R1_powershell_Command" in cov:
        add("run_commands", {"commands": ["powershell.exe -File 's.ps1'"]}, "ok")
    else:
        add("run_commands", {"commands": ["powershell.exe -Command \"$x = 1\""]}, "= : The term '=' is not recognized")

    if "R5_getcontent_no_encoding" in cov:
        add("run_commands", {"commands": ["Get-Content 'x' -Encoding UTF8"]}, "ok")
    else:
        add("run_commands", {"commands": ["Get-Content 'x'"]}, "ok")
    return m


def run_dc(sessdir, case):
    out = subprocess.run([sys.executable, DC, case, "--sess-dir", sessdir], capture_output=True, text=True).stdout
    for ln in out.splitlines():
        if ln.startswith("TOTAL_VIOLATIONS"):
            return int(ln.split()[-1])
    return -1


def main():
    base = tempfile.mkdtemp(prefix="vbt_")
    print("=== BEHAVIOR TEST: сколько спотыканий ОСТАЁТСЯ, если следовать варианту ===")
    print("%-12s  covers(R1..R5)      left  score" % "variant")
    rows = []
    for name, t in rv.VARIANTS:
        cov = covers(t)
        d = os.path.join(base, name, name)
        os.makedirs(d)
        with open(os.path.join(d, name + ".messages.json"), "w", encoding="utf-8") as f:
            json.dump({"messages": sess_following(cov)}, f, ensure_ascii=False)
        left = run_dc(os.path.join(base, name), name)
        s = rv.score(t)
        total = sum(rv.WEIGHTS[k] * s[k] for k in s)
        flags = "".join("X" if ("R%d" % (j + 1)) in " ".join(cov) else "-" for j in range(5))
        # mark covered rules R1..R5
        mark = "".join("X" if any(k.startswith("R%d" % (j + 1)) for k in cov) else "-" for j in range(5))
        rows.append((left, total, name, mark))
        print("%-12s  %-18s  %4d  %5d" % (name, mark, left, total))
    rows.sort()
    print("BEST-BEHAVIOR =", rows[0][2], "(left=%d)" % rows[0][0], "| mark=R1..R5:", rows[0][3])

    fail = 0

    def expect(label, cond):
        nonlocal fail
        if not cond:
            fail += 1
        print(("PASS " if cond else "FAIL ") + label)

    print("=== TESTS ===")
    left = {n: l for (l, s, n, m) in rows}
    expect("V7_full leaves 0 violations", left.get("V7_full") == 0)
    expect("recon-only variants leave >=2 (console/encoding not covered)",
           all(l >= 2 for (l, s, n, m) in rows if n != "V7_full"))
    expect("behavior best is V7_full", rows[0][2] == "V7_full")
    print("TOTAL FAIL =", fail)
    shutil.rmtree(base, ignore_errors=True)
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
