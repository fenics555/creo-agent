# -*- coding: utf-8 -*-
r"""КУЛЬТУРА ДОМА: проверка адресов файлов (24.09.2026).

Сбывшийся кандидат `culture_check` из конспекта «Культура дома»: правила —
`D:\AI\repo\CULTURE_files.md`, канон — `.clinerules` (абзац «ОТЧЁТЫ И ЛОГИ»).
Проверяем ФАКТЫ на диске, а не текст правил: отчёты — в отчётах, логи — в логах,
временное — в урне, конспекты — в памяти дома под гитом, обе копии правил совпадают.

Зов: python dev\culture_check.py    (код возврата 0 = чисто, 1 = есть нарушения)
"""
import hashlib
import sys
from pathlib import Path

try:      # консоль Windows (cp1251/cp866) роняет вывод с эмодзи — урок краха 24.09.2026
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(r"D:\AI")
LOG = ROOT / "log"
URN = LOG / "urn"
REPORTS = LOG / "reports"
REPO = ROOT / "repo"
STUDY = ROOT / "ИЗУЧИТЬ"
BAD, WARN = [], []


def bad(msg):
    BAD.append(msg); print("❌ " + msg)


def warn(msg):
    WARN.append(msg); print("⚠ " + msg)


def ok(msg):
    print("✅ " + msg)


def files_under(d):
    return [f for f in d.rglob("*") if f.is_file()] if d.exists() else []


# --- 1. отчёты: файлы прямо в reports — только REPORT_* --------------------------------------
others = [f.name for f in REPORTS.glob("*") if f.is_file() and not f.name.startswith("REPORT_")]
if others:
    bad("reports: чужих файлов %d (там только REPORT_<задача>_<исполнитель>_<дата>.md): %s"
        % (len(others), ", ".join(others[:6])))
else:
    ok("reports: только отчёты REPORT_* (пакеты в подпапках разрешены)")

# --- 2. корень log: только retention.json ---------------------------------------------------
loose = [f.name for f in LOG.glob("*") if f.is_file() and f.name != "retention.json"]
if loose:
    bad("корень log: лишние файлы %s (логи живут в log\\<программа>\\)" % ", ".join(loose[:6]))
else:
    ok("корень log: чисто (только retention.json)")

# --- 3. урна: в корне urn — только папки исполнителей ---------------------------------------
loose_urn = [f.name for f in URN.glob("*") if f.is_file()]
if loose_urn:
    bad("urn: файлы в корне урны %s (им место в urn\\<исполнитель>\\)" % ", ".join(loose_urn[:6]))
else:
    ok("urn: в корне только папки исполнителей")

# --- 4. урна: пустых папок быть не должно ---------------------------------------------------
empty_urn = [d.name for d in URN.iterdir() if d.is_dir() and not any(d.iterdir())]
if empty_urn:
    warn("urn: пустые папки исполнителей %s (создаются сами при первой записи — можно убрать)"
         % ", ".join(empty_urn))
else:
    ok("urn: пустых папок нет")

# --- 5. временное вне урны ------------------------------------------------------------------
FORBIDDEN = [ROOT / "tmp_find", ROOT / "test_purge", ROOT / "data" / "tmp", ROOT / "tools" / "agent" / "tmp"]
found = []
for d in FORBIDDEN:
    n = len(files_under(d))
    if n:
        found.append("%s (%d)" % (d, n))
if found:
    bad("временное вне урны: %s — место ему в log\\urn\\<исполнитель>\\" % "; ".join(found))
else:
    ok("временное вне урны не найдено")

proba_temp = []
for f in (ROOT / "PROBA").glob("*"):
    if not f.is_file():
        continue
    if not (f.name.endswith(("_run.txt", "_err.txt", "_out.txt")) or f.name.startswith("probe")):
        continue
    # дом держит часть прототипов осознанно: если имя упомянуто в скиллах/доках — это не мусор
    ref = any(f.name in p.read_text(encoding="utf-8", errors="ignore")
              for p in list((REPO).rglob("*.md"))[:400])
    if not ref:
        proba_temp.append(f.name)
if proba_temp:
    bad("PROBA: выводы проб лежат в PROBA %s (место — урна)" % ", ".join(proba_temp[:6]))
else:
    ok("PROBA: выводов проб не найдено (осознанно оставленные прототипы не считаем)")

# --- 6. конспекты живут в памяти дома (repo\ИЗУЧЕНО), а не в ИЗУЧИТЬ (тот вне гита) ----------
legacy = [d.name for d in STUDY.iterdir() if d.is_dir() and (d / "STUDY_NOTES.md").exists()] \
    if STUDY.exists() else []
if legacy:
    bad("конспекты вне памяти дома: %s — перенести в repo\\ИЗУЧЕНО\\<тема>\\" % ", ".join(legacy))
else:
    ok("конспектов в ИЗУЧИТЬ нет (память дома — repo\\ИЗУЧЕНО)")

notes = [d for d in (REPO / "ИЗУЧЕНО").iterdir() if d.is_dir() and (d / "STUDY_NOTES.md").exists()] \
    if (REPO / "ИЗУЧЕНО").exists() else []
if notes:
    ok("конспектов в repo\\ИЗУЧЕНО: %d (%s)" % (len(notes), ", ".join(d.name for d in notes)))
else:
    warn("в repo\\ИЗУЧЕНО конспектов пока нет — начни study_start")

# --- 7. обе копии .clinerules обязаны совпадать ---------------------------------------------
a, b = ROOT / ".clinerules", REPO / ".clinerules"
if not (a.exists() and b.exists()):
    bad(".clinerules: нет одной из копий (%s / %s)" % (a, b))
elif hashlib.sha1(a.read_bytes()).hexdigest() != hashlib.sha1(b.read_bytes()).hexdigest():
    bad(".clinerules: копии в корне и в repo РАЗОШЛИСЬ — синхронизировать")
else:
    ok(".clinerules: копии в корне и в repo совпадают")

# --- 8. retention.json: ключи только для существующих папок log ------------------------------
import json  # noqa: E402

try:
    ret = json.loads((LOG / "retention.json").read_text(encoding="utf-8"))
    dirs = {d.name for d in LOG.iterdir() if d.is_dir()}
    dead = [k for k in ret if k not in dirs and k != "root"]
    if dead:
        bad("retention.json: ключи без папки — %s (срок ни за чем не следит)" % ", ".join(dead))
    else:
        ok("retention.json: сроки только для существующих каталогов")
except Exception as e:
    bad("retention.json: не читается (%s)" % e)

# --- 9. data\backup: пустых папок быть не должно ---------------------------------------------
bk = ROOT / "data" / "backup"
empty_bk = [d.name for d in bk.iterdir() if d.is_dir() and not any(d.iterdir())] if bk.exists() else []
if empty_bk:
    bad("data\\backup: пустые папки %s" % ", ".join(empty_bk[:6]))
else:
    ok("data\\backup: пустых папок нет")

# --- 10. правила и указатели на месте --------------------------------------------------------
for p in (REPO / "CULTURE_files.md", REPO / "ИЗУЧЕНО" / "README.md",
          REPO / "crash" / "SKILL_crash_constitution.md",
          ROOT / "tools" / "agent" / "log_clean" / "engine.py"):
    if not p.exists():
        bad("нет файла правил: %s" % p)
if not [1 for p in (REPO / "CULTURE_files.md", REPO / "ИЗУЧЕНО" / "README.md")
        if not p.exists()]:
    ok("правила и указатели на месте (карта, ИЗУЧЕНО, конституция крахов, движок уборки)")

print("")
print("ИТОГ: нарушений %d, предупреждений %d" % (len(BAD), len(WARN)))
print("КУЛЬТУРА: " + ("ЧИСТО" if not BAD else "ЕСТЬ НАРУШЕНИЯ — см. ❌ выше"))
sys.exit(1 if BAD else 0)

