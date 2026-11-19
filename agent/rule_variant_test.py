import os, re, sys, hashlib, json, subprocess, tempfile, shutil

REPO = r"D:\AI\repo"
CL = r"D:\AI\.clinerules"
CLR = os.path.join(REPO, ".clinerules")
EG = os.path.join(REPO, "SKILL_edit_gotchas.md")
DC = r"D:\AI\tools\agent\doctrine_check.py"

# Кандидаты формулировки обязательной разведки (что вставить в красные линии).
VARIANTS = [
    ("V0_installed",
     "\U0001F534 РАЗВЕДКА ОБЯЗАТЕЛЬНА (ЛЮБАЯ МОДЕЛЬ): ПЕРЕД чтением файла И ПЕРЕД обходом папки — СНАЧАЛА разведка: файл — размер в байтах/строки; папка — число детей и глубина. Регламент: `SKILL_recon.md` \u00a70\u2013\u00a72; маршрут правки — `SKILL_edit_gotchas.md` \u00a70. Пропуск разведки = причина петель."),
    ("V1_short",
     "ПЕРЕД чтением файла или папки — сначала разведка: размер в байтах/строках, число детей/глубина. Скилл SKILL_recon.md."),
    ("V2_mandate",
     "\U0001F534 РАЗВЕДКА ОБЯЗАТЕЛЬНА (ЛЮБАЯ МОДЕЛЬ): ПЕРЕД чтением файла И обходом папки — СНАЧАЛА размер (байты/строки) и число детей/глубина; регламент SKILL_recon.md \u00a70\u2013\u00a72."),
    ("V3_exclaim",
     "СТОП! ПЕРЕД read_files и обходом папки сначала получи метрики: файл — Get-Item Length + число строк; папка — Get-ChildItem (без -Recurse) и .Count. Пропуск = лимит и петля. SKILL_recon.md \u00a71\u2013\u00a72."),
    ("V4_law",
     "[\u0417\u0410\u041a\u041e\u041d \u0414\u041e\u041c\u0410] Любая модель ОБЯЗАНА: разведка ДО чтения — файл (байты/строки), папка (дети/глубина). Не рекурсить незнакомое дерево. Регламент SKILL_recon.md; маршрут правки SKILL_edit_gotchas.md \u00a70."),
    ("V5_fork",
     "Разведка прежде чтения: файл > 40 КБ — только диапазонами; папка — глубина 1 + счётчики. SKILL_recon.md."),
    ("V6_bold",
     "ОБЯЗАТЕЛЬНО: разведка ДО чтения файла/папки (байты, строки, дети, глубина) — иначе лимит и петля. Регламент SKILL_recon.md \u00a70\u2013\u00a72; правка — SKILL_edit_gotchas.md \u00a70."),
    ("V7_full",
     "\U0001F534 [ЗАКОН] РАЗВЕДКА ОБЯЗАТЕЛЬНА (ЛЮБАЯ МОДЕЛЬ): перед чтением/обходом — метрики (Get-Item Length; Get-ChildItem без -Recurse); правка — editor с old_text; UTF-8 — с -Encoding; НЕ powershell -Command с $var. Регламент SKILL_recon.md \u00a70\u2013\u00a72, правка SKILL_edit_gotchas.md \u00a70/\u00a74. Иначе — лимит и петля."),
]

WEIGHTS = {"imperative": 2, "skill_ref": 2, "section": 1, "metrics": 2,
           "antiloop": 1, "edit_route": 1, "universal": 1, "compact": 1}


def score(t):
    return {
        "imperative": 1 if re.search(r"ОБЯЗАН|ОБЯЗАТЕЛЬН|СТОП|ПЕРЕД", t) else 0,
        "skill_ref": 1 if "SKILL_recon.md" in t else 0,
        "section": 1 if "\u00a7" in t else 0,
        "metrics": 1 if re.search(r"байт|строк|дет|глубин|Length|Count", t) else 0,
        "antiloop": 1 if re.search(r"петл|лимит", t) else 0,
        "edit_route": 1 if "SKILL_edit_gotchas" in t else 0,
        "universal": 1 if re.search(r"ЛЮБАЯ|Любая|модел", t) else 0,
        "compact": 1 if len(t) <= 300 else 0,
    }


def main():
    rows = []
    for name, t in VARIANTS:
        s = score(t)
        total = sum(WEIGHTS[k] * s[k] for k in s)
        rows.append((total, name, len(t), s))
    rows.sort(reverse=True)
    print("=== RULE VARIANT SCORING (max %d) ===" % sum(WEIGHTS.values()))
    print("score  variant       len  " + " ".join("%-9s" % k[:9] for k in WEIGHTS))
    for total, name, ln, s in rows:
        print("%5d  %-12s %4d  " % (total, name, ln) + " ".join("%-9d" % s[k] for k in WEIGHTS))
    best = rows[0]
    print("BEST =", best[1], "score", best[0])

    # where is the mandate actually installed?
    try:
        cl = open(CL, encoding="utf-8").read()
    except Exception as e:
        print("cannot read law:", e)
        return
    found = [n for n, t in VARIANTS if t in cl]
    print("INSTALLED variant in law:", found or "NONE (law wording differs)")
    print("law has mandatory marker:", "РАЗВЕДКА ОБЯЗАТЕЛЬНА" in cl)
    print("edit-gotchas Get-Content finding present:", "-Encoding UTF8" in open(EG, encoding="utf-8").read())

    # ================= TESTS =================
    fail = 0

    def expect(label, cond):
        nonlocal fail
        if not cond:
            fail += 1
        print(("PASS " if cond else "FAIL ") + label)

    def total(t):
        s = score(t)
        return sum(WEIGHTS[k] * s[k] for k in s)

    print("=== TESTS ===")
    expect("scorer: strong variant >= 10", total(dict(VARIANTS)["V4_law"]) >= 10)
    expect("scorer: vague variant <= 4", total("Читай файлы аккуратно и не спеши.") <= 4)
    for n, t in VARIANTS:
        expect("well-formed: refs recon skill [" + n + "]", "SKILL_recon.md" in t)
    expect("law copies synced",
           hashlib.sha256(open(CL, "rb").read()).hexdigest() == hashlib.sha256(open(CLR, "rb").read()).hexdigest())
    expect("law has mandatory marker", "РАЗВЕДКА ОБЯЗАТЕЛЬНА" in cl)
    expect("law refs recon skill", "SKILL_recon.md" in cl)
    eg = open(EG, encoding="utf-8").read()
    expect("edit_gotchas: S0 route present", "МАРШРУТ ПЕРЕД ПРАВКОЙ" in eg)
    expect("edit_gotchas: Get-Content finding present", "-Encoding UTF8" in eg)
    dc = open(DC, encoding="utf-8").read()
    expect("doctrine_check: has read-truncated rule", "read_truncated" in dc)
    expect("doctrine_check: has recursive rule", "recursive_scan" in dc)
    expect("doctrine_check: has Get-Content encoding rule", "getcontent_no_encoding" in dc)

    # behavioral: doctrine_check flags a Get-Content-without-encoding fixture
    base = tempfile.mkdtemp(prefix="rv_")
    d = os.path.join(base, "c1")
    os.makedirs(d)
    msgs = [
        {"role": "assistant", "content": [{"type": "tool_use", "id": "c1", "name": "run_commands", "input": {"commands": ["Get-Content 'x.json'"]}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "c1", "content": [{"result": "ok", "query": ""}]}]},
    ]
    with open(os.path.join(d, "c1.messages.json"), "w", encoding="utf-8") as f:
        json.dump({"messages": msgs}, f, ensure_ascii=False)
    out = subprocess.run([sys.executable, DC, "c1", "--sess-dir", base], capture_output=True, text=True).stdout
    expect("doctrine_check flags Get-Content w/o -Encoding", "R5_getcontent_no_encoding" in out and "VIOLATION" in out)
    shutil.rmtree(base, ignore_errors=True)

    print("TOTAL FAIL =", fail)
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
