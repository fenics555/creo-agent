# -*- coding: utf-8 -*-
# skills_check: crash\ instances + root/Prog name headers. Report is written by python in UTF-8.
import os
import re

BASELINE = r"D:\AI\tools\agent\data\skills_check_baseline.txt"
REPORT = r"D:\AI\log\skills_check\skills_check_report.txt"
CRASH = r"D:\AI\repo\crash"
ROOTS = [r"D:\AI\repo", r"D:\AI\repo\Prog"]
PTR = "\u044d\u0442\u043e\u0442 \u0444\u0430\u0439\u043b \u2014 \u0443\u043a\u0430\u0437\u0430\u0442\u0435\u043b\u044c"
ERRF = "\u041e\u0428\u0418\u0411\u041a\u0410"
NAMERX = re.compile(r"^\s*#?\s*name:\s*([\w\-]+)", re.M)
HEAD_LINES = 40   # шапка — это НАЧАЛО файла: у сборников (SKILL_CHARGE*) ниже вшиты тела
                  # чужих скиллов со своими name:, и поиск по всему файлу давал ложный «mismatch»
STAGE = {"SKILL_crash_constitution.md", "SKILL_crash_index.md"}   # документы темы, а не экземпляры болезни


def head(t):
    return "\n".join(t.splitlines()[:HEAD_LINES])


def canon(s):
    # canon: дефис и подчёркивание в именах эквивалентны; переименование файла ради
    # прохождения проверки = нарушение, цитаты дома старше проверки (решение 22.09)
    return s.replace("-", "_")
ERRRX = re.compile(r"^\s*" + ERRF + r"\s*[(:]", re.M)


def read(p):
    # utf-8-sig: BOM в начале файла не должен прятать шапку name: (находка ноги 3)
    with open(p, "r", encoding="utf-8-sig", errors="replace") as f:
        return f.read()


violations = []
notes = []

if os.path.isdir(CRASH):
    for fn in sorted(os.listdir(CRASH)):
        if not fn.endswith(".md"):
            continue
        p = os.path.join(CRASH, fn)
        t = read(p)
        # 22.09 decision: a one-line pointer inside crash\ is waived from the name rule
        if PTR in t and len([l for l in t.split("\n") if l.strip()]) <= 1:
            notes.append("%s: pointer, name check waived (decision 22.09)" % fn)
            continue
        exp = fn.replace("SKILL_", "").replace(".md", "")
        m = NAMERX.search(head(t))
        if not m:
            violations.append("%s: missing name field" % fn)
        elif canon(m.group(1)) != canon(exp):
            violations.append("%s: name mismatch (found %s, expected %s)" % (fn, m.group(1), exp))
        if fn in STAGE:
            # конституция крахов и индекс — документы темы (навигация и рамки), полей болезни не имеют
            continue
        if "executor:" not in t:
            violations.append("%s: missing executor field" % fn)
        if not ERRRX.search(t):
            violations.append("%s: missing %s (grep field)" % (fn, ERRF))

# root and Prog: outside crash\ only the name header is checked, and only when it exists
for root in ROOTS:
    label = os.path.basename(root) or "repo"
    if not os.path.isdir(root):
        continue
    for fn in sorted(os.listdir(root)):
        p = os.path.join(root, fn)
        if not (fn.startswith("SKILL_") and fn.endswith(".md")) or not os.path.isfile(p):
            continue
        t = read(p)
        exp = fn.replace("SKILL_", "").replace(".md", "")
        m = NAMERX.search(head(t))
        if not m:
            notes.append("%s/%s: text passport, no name header (observation only)" % (label, fn))
        elif canon(m.group(1)) != canon(exp):
            violations.append("%s/%s: name mismatch (found %s, expected %s)" % (label, fn, m.group(1), exp))

lines = []
lines.append("skills_check report  " + "date: see file mtime")
lines.append("canon: дефис и подчёркивание в именах эквивалентны; переименование файла ради прохождения проверки = нарушение, цитаты дома старше проверки (решение 22.09)")
lines.append("грабли: после правки .py обязателен ПРОГОН (не только py_compile); вывод читать процессом без переадресации «>» (PowerShell отдаёт пустой файл); кириллический путь в git-командах передавать питоном")
lines.append("")
lines.append("violations: %d" % len(violations))
for v in violations:
    lines.append("- " + v)
lines.append("")
lines.append("notes (not violations): %d" % len(notes))
for n in notes:
    lines.append("- " + n)

# baseline delta (same contract as before: new violations must not drown in the background)
delta = []
try:
    cur = sorted(violations)
    prev = None
    if os.path.exists(BASELINE):
        prev = [l.rstrip("\n") for l in open(BASELINE, encoding="utf-8") if l.strip()]
    if prev is None:
        open(BASELINE, "w", encoding="utf-8").write("\n".join(cur) + "\n")
        lines.append("")
        lines.append("baseline created: %d" % len(cur))
    else:
        new = [v for v in cur if v not in prev]
        fixed = [v for v in prev if v not in cur]
        for v in new:
            delta.append("NEW: " + v)
        lines.append("")
        lines.append("delta: new=%d closed=%d" % (len(new), len(fixed)))
        lines.extend(delta)
        if not new and not fixed:
            lines.append("stable: %d" % len(cur))
except Exception as e:
    lines.append("delta err: %r" % e)

os.makedirs(os.path.dirname(REPORT), exist_ok=True)
with open(REPORT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

print("violations=%d notes=%d report=%s" % (len(violations), len(notes), REPORT))
for v in violations:
    print("V: " + v.encode("ascii", "backslashreplace").decode("ascii"))
for n in notes:
    print("N: " + n.encode("ascii", "backslashreplace").decode("ascii"))