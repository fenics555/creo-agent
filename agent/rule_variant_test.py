import os, re, sys

REPO = r"D:\AI\repo"
CL = r"D:\AI\.clinerules"
EG = os.path.join(REPO, "SKILL_edit_gotchas.md")

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
]

WEIGHTS = {"imperative": 2, "skill_ref": 2, "section": 1, "metrics": 2,
           "antiloop": 1, "edit_route": 1, "universal": 1, "compact": 1}


def score(t):
    return {
        "imperative": 1 if re.search(r"ОБЯЗАН|СТОП|ПЕРЕД", t) else 0,
        "skill_ref": 1 if "SKILL_recon.md" in t else 0,
        "section": 1 if "\u00a7" in t else 0,
        "metrics": 1 if re.search(r"байт|строк|дет|глубин", t) else 0,
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
    sys.exit(0)


if __name__ == "__main__":
    main()
