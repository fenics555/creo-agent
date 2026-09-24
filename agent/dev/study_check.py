# -*- coding: utf-8 -*-
r"""ПРОВЕРКА ИНСТРУМЕНТА КОНСПЕКТА (study_tools, метод хозяина 24.09.2026).

Проверяем не текст файла, а работу: завёл конспект → записал два куска → прикинул скилл
(заготовка в repo\BACKLOG_tools.md) → посмотрел статус. В конце убираем за собой:
строку пробы из репо снимаем, папку пробы ПЕРЕНОСИМ в урну (не удаляем — правило дома).
"""
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

import tools_registry as TR  # noqa: E402
import study_tools as ST  # noqa: E402

try:      # консоль Windows (cp1251/cp866) калечит эмодзи и роняет вывод — крах 24.09.2026
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

OK = [True]
TOPIC = "_проба_инструмента"
SKILL = "проба_инструмента"
SKILL2 = "проба_неудача"      # скилл, прикинутый из НЕУДАЧИ (крах 24.09.2026: объявлен не сразу)


def chk(name, cond, extra=""):
    print(("✅ " if cond else "❌ ") + name + (("  — " + str(extra)) if extra != "" else ""))
    if not cond:
        OK[0] = False


# --- 1. инструмент зарегистрирован ---------------------------------------------------------
names = [t["name"] for t in TR.TOOLS]
chk("в реестре есть study_start", "study_start" in names)
chk("в реестре есть study_note", "study_note" in names)
chk("в реестре есть study_skill", "study_skill" in names)
chk("в реестре есть study_status", "study_status" in names)
chk("в реестре есть study_fail (неудачи пишем сразу)", "study_fail" in names)
chk("в реестре есть study_progress (ход по папке)", "study_progress" in names)
chk("study_skill пишущий → под согласованием", (TR.get("study_skill") or {}).get("approval") is True)
chk("study_note без согласования (иначе конспект не пишется)", (TR.get("study_note") or {}).get("approval") is False)

# --- 2. заводим конспект -------------------------------------------------------------------
note = ST._note(TOPIC)
if note.parent.exists():
    shutil.rmtree(note.parent, ignore_errors=True)      # своя папка пробы от прошлого прогона
r1 = ST.study_start(topic=TOPIC, source="проверка инструмента", why="убедиться, что конспект пишется")
chk("конспект заведён", note.exists(), r1.splitlines()[0] if r1 else "")
head = note.read_text(encoding="utf-8") if note.exists() else ""
chk("в шапке есть источник и цель", "**Источник:**" in head and "**Цель:**" in head)
chk("в шапке названы правила ведения записей", "Как ведём записи" in head)
chk("в шапке сказано: неудачу пишем СРАЗУ", "study_fail" in head and "СРАЗУ" in head)
chk("в шапке есть ход по папке", "study_progress" in head)
chk("в шапке указана урна для временного", "urn" in head)

# --- 3. два куска ---------------------------------------------------------------------------
ST.study_note(topic=TOPIC, chunk="кусок 1: шапка", text="понял, как заводится конспект")
r3 = ST.study_note(topic=TOPIC, chunk="кусок 2: записи", text="понял, как пишутся куски", skill=SKILL)
body = note.read_text(encoding="utf-8")
chk("кусков стало 2", len(ST.re.findall(r"^## \d+\.", body, ST.re.M)) == 2)
chk("в каждой записи есть вопрос про скилл", body.count("**Нужен ли скилл?**") == 2)
chk("в записи про скилл написано «да»", "да → заготовка" in body, r3.splitlines()[-1] if r3 else "")
chk("кандидат отмечен в конспекте", "## Кандидаты в скиллы" in body)

# --- 4. заготовка скилла в репо -------------------------------------------------------------
bl = ST.BACKLOG.read_text(encoding="utf-8")
line1 = [l for l in bl.splitlines() if l.startswith("- %s ·" % SKILL)]
chk("заготовка скилла появилась в BACKLOG_tools.md", len(line1) == 1, line1)
chk("статус заготовки — замысел", "· замысел ·" in (line1[0] if line1 else ""))
ST.study_skill(topic=TOPIC, skill=SKILL, why="проверка", ready="черновик")
bl2 = ST.BACKLOG.read_text(encoding="utf-8")
line2 = [l for l in bl2.splitlines() if l.startswith("- %s ·" % SKILL)]
chk("повторный вызов не плодит дублей", len(line2) == 1, line2)
chk("статус обновился на черновик", "· черновик ·" in (line2[0] if line2 else ""))

# --- 4б. неудача — пишется СРАЗУ и в свой раздел -------------------------------------------
r4 = ST.study_fail(topic=TOPIC, what="выбрал не тот инструмент", tool="search_kb",
                   result="поиск вернул пустоту, вопрос был про файл, а не про базу",
                   fix="сначала read_file по пути, search_kb только по базе знаний", skill=SKILL2)
body = note.read_text(encoding="utf-8")
chk("раздел «ЧТО НЕ ПОЛУЧИЛОСЬ» появился", "## ЧТО НЕ ПОЛУЧИЛОСЬ" in body)
chk("неудача пронумерована", "### ❌ 1." in body)
chk("в неудаче записан инструмент", "инструмент: search_kb" in body)
chk("в неудаче записан вывод (что делать)", "read_file по пути" in body, (r4 or "").splitlines()[0])
bl_f = ST.BACKLOG.read_text(encoding="utf-8")
chk("скилл из неудачи попал в заготовки", ("- %s ·" % SKILL2) in bl_f)

# --- 4в. ход изучения: файл за файлом, папка за папкой --------------------------------------
ST.study_progress(topic=TOPIC, done="20 из 60 файлов, папка creo_bom_js", next_step="внутри: excel_export.py")
b1 = note.read_text(encoding="utf-8")
chk("блок хода изучения появился", "**Ход изучения:**" in b1)
chk("видно, что просмотрено и что дальше", "20 из 60" in b1 and "excel_export.py" in b1)
ST.study_progress(topic=TOPIC, done="35 из 60 файлов, папка creo_bom_js", next_step="внутри: family_table_file.py")
b2 = note.read_text(encoding="utf-8")
chk("повторное обновление НЕ плодит блоки", b2.count("<!-- ПРОГРЕСС -->") == 1)
chk("ход обновился", "35 из 60" in b2 and "20 из 60" not in b2)
chk("блок хода стоит до записей (виден сразу)", b2.find("**Ход изучения:**") < b2.find("\n## 1."))

# --- 5. статус ------------------------------------------------------------------------------
st = ST.study_status()
chk("study_status видит конспект", TOPIC in st)
chk("study_status показывает заготовку", SKILL in st)
chk("study_status показывает неудачу", "неудач 1" in st, [l for l in st.splitlines() if "неудач" in l])
chk("study_status показывает ход изучения", "35 из 60" in st)

# --- 6. уборка за собой ---------------------------------------------------------------------
keep = [l for l in bl2.splitlines() if not l.startswith("- %s ·" % SKILL) and not l.startswith("- %s ·" % SKILL2)]
ST.BACKLOG.write_text("\n".join(keep).rstrip("\n") + "\n", encoding="utf-8")
urn = Path(r"D:\AI\log\urn\cline") / TOPIC
urn.parent.mkdir(parents=True, exist_ok=True)
if note.parent.exists():
    if urn.exists():
        shutil.rmtree(urn, ignore_errors=True)
    shutil.move(str(note.parent), str(urn))              # перенос, не удаление
bl3 = ST.BACKLOG.read_text(encoding="utf-8")
chk("строка пробы снята с репо", ("- %s ·" % SKILL) not in bl3)
chk("строка неудачи снята с репо", ("- %s ·" % SKILL2) not in bl3)
chk("папка пробы переехала в урну", urn.exists() and not note.parent.exists(), urn)

print("")
print("ИТОГ: " + ("ВСЁ ЗЕЛЁНОЕ — конспект и заготовки скиллов работают" if OK[0] else "ЕСТЬ ОШИБКИ — см. ❌ выше"))
sys.exit(0 if OK[0] else 1)
