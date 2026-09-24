# -*- coding: utf-8 -*-
r"""study_tools — КОНСПЕКТ ИЗУЧЕНИЯ (метод хозяина, 24.09.2026).

Метод дословно: «изучил кусок — записал; дальше изучил — ещё записал; посмотрел: нужен ли скилл? —
тут же прикинул будущий скилл».

Куда пишем (карта дома: `D:\AI\repo\CULTURE_files.md`):
  * `D:\AI\repo\ИЗУЧЕНО\<тема>\STUDY_NOTES.md` — конспект (ПАМЯТЬ ДОМА под гитом, уборщик его НЕ чистит);
  * `D:\AI\ИЗУЧИТЬ\<тема>\` — источники для чтения (большие библиотеки; этот каталог ВНЕ гита);
  * `D:\AI\repo\BACKLOG_tools.md` — заготовки скиллов, раздел «ЗАГОТОВКИ СКИЛЛОВ» (репо под гитом);
  * временное (выборки из больших файлов, дампы) — в урну `D:\AI\log\urn\<исполнитель>\<тема>\`.

Почему конспект не в лог: из конспекта рождаются скиллы (`SKILL_*.md` → карта `SKILL_CHARGE.md`),
а лог живёт 30–56 дней и исчезает.
"""
import datetime
import os
import re
import threading
from pathlib import Path

from core import log, REPO

STUDY_ROOT = REPO / "ИЗУЧЕНО"           # конспекты — ПАМЯТЬ ДОМА под гитом: живая находка 24.09.2026
SRC_ROOT = Path(r"D:\AI\ИЗУЧИТЬ")       # источники (большие библиотеки, вне гита — их и читаем)
BACKLOG = REPO / "BACKLOG_tools.md"
URN = Path(r"D:\AI\log\urn")
HEAD = "## ЗАГОТОВКИ СКИЛЛОВ"
STATUSES = ("замысел", "черновик", "готов")


def _who():
    """Кто пишет: клиент из потока запроса, иначе `AI_EXECUTOR` (скрипт вне агента), иначе agent."""
    try:
        return (getattr(threading.current_thread(), "_tokclient", None)
                or os.environ.get("AI_EXECUTOR") or "agent")
    except Exception:
        return "agent"


def _now():
    return datetime.datetime.now().strftime("%d.%m.%Y %H:%M")


def _topic(name):
    """Имя темы → безопасное имя папки: без путей, точек и разделителей."""
    return re.sub(r"[^A-Za-zА-Яа-яЁё0-9_\- ]+", "", str(name or "")).strip()[:60]


def _note(topic):
    """Конспект темы. Новые — в `repo\\ИЗУЧЕНО\\<тема>\\` (под гитом, не потеряется).
    Если тема уже начата в старом месте (`D:\\AI\\ИЗУЧИТЬ\\<тема>\\`) — пишем туда же, чтобы
    не раздваивать одну тему на два файла."""
    t = _topic(topic)
    legacy = SRC_ROOT / t / "STUDY_NOTES.md"
    if legacy.exists():
        return legacy
    return STUDY_ROOT / t / "STUDY_NOTES.md"


def _add_backlog(skill, ready, why, source):
    """Строка заготовки в repo\\BACKLOG_tools.md: одна строка на скилл, статус обновляется."""
    name = _topic(skill)
    if not name:
        return "имя скилла пустое — ничего не записано"
    st = ready if ready in STATUSES else "замысел"
    line = "- %s · %s · %s · %s" % (name, st, why or "—", source or "—")
    if not BACKLOG.exists():
        BACKLOG.write_text("# BACKLOG TOOLS\n\n%s (изучено → скилл)\n\n%s\n" % (HEAD, line), encoding="utf-8")
    else:
        lines = BACKLOG.read_text(encoding="utf-8", errors="ignore").splitlines()
        i = next((k for k, l in enumerate(lines) if l.startswith(HEAD)), None)
        if i is None:
            lines += ["", HEAD + " (изучено → скилл)", "", line]
        else:
            j = next((k for k in range(i + 1, len(lines)) if lines[k].startswith("## ")), len(lines))
            hit = next((k for k in range(i + 1, j) if lines[k].startswith("- %s ·" % name)), None)
            if hit is not None:
                lines[hit] = line
            else:
                while j > i + 1 and not lines[j - 1].strip():
                    j -= 1
                lines.insert(j, line)
            lines = [l for l in lines if not l.strip().startswith("(пока пусто")]
        BACKLOG.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")
    log("study: заготовка скилла %s (%s)" % (name, st))
    return "Заготовка скилла: %s · %s → %s" % (name, st, BACKLOG)


def _add_candidate(topic, skill, ready, why):
    """Отметить кандидата в самом конспекте (раздел «Кандидаты в скиллы»)."""
    p = _note(topic)
    if not p.exists():
        return ""
    body = p.read_text(encoding="utf-8", errors="ignore")
    line = "- %s · %s · %s" % (skill, ready, why or "—")
    if re.search(r"^- %s ·" % re.escape(skill), body, re.M):
        return "Отмечено в конспекте: %s" % p
    with open(p, "a", encoding="utf-8") as f:
        if "\n## Кандидаты в скиллы" in body:
            f.write(line + "\n")
        else:
            f.write("\n## Кандидаты в скиллы\n\n" + line + "\n")
    return "Отмечено в конспекте: %s" % p


def study_start(topic="", source="", why="", **kw):
    """Завести конспект изучения (шапка + правило записи)."""
    t = _topic(topic)
    if not t:
        return "нужна тема: study_start topic=<имя> source=<папка/файл> why=<цель>"
    p = _note(t)
    if p.exists():
        return "конспект уже есть: %s\nпродолжай: study_note topic=%s chunk=<что читал> text=<что понял>" % (p, t)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "# Конспект изучения: %s\n\n"
        "**Статус:** живое чтение, начат %s (%s).\n"
        "**Источник:** %s\n"
        "**Цель:** %s\n"
        "**Карта скиллов дома:** `%s\\SKILL_index.md` — сверить, чтобы не выдумывать заново.\n\n"
        "**Где живёт конспект:** `%s\\<тема>\\STUDY_NOTES.md` (память дома под гитом). Источники для чтения —\n"
        "в `%s` (большие библиотеки вне гита).\n\n"
        "**Как ведём записи (правило дома, 24.09.2026):**\n"
        "1. важное из куска — `study_note` (запись ДО следующего куска);\n"
        "2. **что не получилось — `study_fail` СРАЗУ** (выбрал не тот инструмент, вылет, ошибка, пустой ответ);\n"
        "3. ход по папке — `study_progress` (файл за файлом, папка за папкой: что просмотрено, что дальше);\n"
        "4. на каждой записи вопрос «нужен ли скилл?» — `study_skill` (заготовки в `%s`).\n"
        "Временное (выборки, дампы, сырые выводы проб) — в урну `%s\\%s\\%s\\`.\n\n---\n"
        % (t, _now(), _who(), source or "не указан", why or "не указана",
           REPO, STUDY_ROOT, SRC_ROOT, BACKLOG, URN, _who(), t), encoding="utf-8")
    log("study: начат конспект %s" % p)
    return ("Конспект заведён: %s\n"
            "Дальше: прочитал кусок → study_note topic=%s chunk=<что читал> text=<что понял и что осталось>"
            % (p, t))


def study_note(topic="", chunk="", text="", skill="", **kw):
    """Записать очередной кусок (ДО следующего) и тут же ответить: нужен ли скилл?"""
    t = _topic(topic)
    p = _note(t)
    if not t or not p.exists():
        return "нет такого конспекта: %s\nначни: study_start topic=<имя> source=<что изучаем> why=<цель>" % p
    body = p.read_text(encoding="utf-8", errors="ignore")
    n = len(re.findall(r"^## \d+\.", body, re.M)) + 1
    sk = ("да → заготовка «%s»" % _topic(skill)) if skill else "нет (правило пока не выкристаллизовалось)"
    rec = ("\n## %d. %s\n_%s, %s_\n\n%s\n\n**Нужен ли скилл?** %s\n"
           % (n, (chunk or "кусок").strip(), _now(), _who(), (text or "(текст не записан)").strip(), sk))
    with open(p, "a", encoding="utf-8") as f:
        f.write(rec)
    extra = ""
    if skill:
        extra = "\n" + _add_backlog(skill, "замысел", "из конспекта %s" % t, "запись %d" % n)
        extra += "\n" + _add_candidate(t, _topic(skill), "замысел", "из записи %d" % n)
    log("study: %s — запись %d" % (t, n))
    return "Записано: кусок %d → %s\nПравило: следующий кусок — новая запись.%s" % (n, p, extra)


def study_skill(topic="", skill="", why="", ready="замысел", **kw):
    """Прикинуть будущий скилл: заготовка в repo\\BACKLOG_tools.md + отметка в конспекте."""
    if not skill:
        return ("нужно имя скилла: study_skill skill=<имя> why=<почему нужен> "
                "ready=замысел|черновик|готов topic=<конспект>")
    t = _topic(topic)
    st = ready if ready in STATUSES else "замысел"
    msg = _add_backlog(skill, st, why, ("из конспекта %s" % t) if t else "—")
    if t:
        add = _add_candidate(t, _topic(skill), st, why or "—")
        if add:
            msg += "\n" + add
    if st == "готов":
        msg += ("\n«Готов» = скилл `SKILL_<имя>.md` в репо: положи туда правила, потом `skills_map rebuild=1` —\n"
                "он войдёт в карту `SKILL_CHARGE.md` и в маршрутизацию агента.")
    return msg


FAIL_HEAD = "## ЧТО НЕ ПОЛУЧИЛОСЬ (пишется СРАЗУ)"
PROG_A, PROG_B = "<!-- ПРОГРЕСС -->", "<!-- /ПРОГРЕСС -->"


def _append_in_section(p, head, rec):
    """Дописать запись в раздел `head` (создать при отсутствии), не ломая порядок разделов."""
    body = p.read_text(encoding="utf-8", errors="ignore")
    i = body.find(head)
    if i < 0:
        cand = body.find("\n## Кандидаты в скиллы")
        block = "\n" + head + "\n" + rec
        body = (body[:cand] + block + body[cand:]) if cand > 0 else (body.rstrip("\n") + "\n" + block)
    else:
        j = body.find("\n## ", i + len(head))
        body = (body[:j] + rec + body[j:]) if j > 0 else (body.rstrip("\n") + "\n" + rec)
    p.write_text(body, encoding="utf-8")


def study_fail(topic="", what="", tool="", result="", fix="", skill="", **kw):
    """ЗАПИСАТЬ НЕУДАЧУ СРАЗУ: выбран не тот инструмент, вылет, ошибка, пустой ответ.

    Правило хозяина 24.09.2026: что не получилось — обязательно и немедленно в конспект.
    Иначе через час остаётся «почему-то не сработало» без инструмента и текста ошибки."""
    t = _topic(topic)
    p = _note(t)
    if not t or not p.exists():
        return "нет такого конспекта: %s\nначни: study_start topic=<имя> source=<что изучаем> why=<цель>" % p
    body = p.read_text(encoding="utf-8", errors="ignore")
    n = len(re.findall(r"^### ❌ \d+\.", body, re.M)) + 1
    sk = ("да → заготовка «%s»" % _topic(skill)) if skill else "нет"
    rec = ("\n### ❌ %d. %s\n_%s, %s · инструмент: %s_\n\n"
           "**Чем кончилось:** %s\n\n**Вывод и что делать в следующий раз:** %s\n\n**Нужен скилл:** %s\n"
           % (n, (what or "неудача").strip(), _now(), _who(), (tool or "не записан").strip(),
              (result or "не записано").strip(), (fix or "не записано").strip(), sk))
    _append_in_section(p, FAIL_HEAD, rec)
    extra = ""
    if skill:
        extra = "\n" + _add_backlog(skill, "замысел", "из неудачи: %s" % (what or "—"), "конспект %s" % t)
        extra += "\n" + _add_candidate(t, _topic(skill), "замысел", "из неудачи «%s»" % (what or "—"))
    log("study: %s — неудача %d" % (t, n))
    return ("Неудача записана: ❌ %d → %s\n"
            "Так и надо: неудачу пишем СРАЗУ, пока помним инструмент и текст ошибки.%s" % (n, p, extra))


def study_progress(topic="", done="", next_step="", **kw):
    """Ход изучения: что просмотрено и что дальше — «файл за файлом, папка за папкой».

    Блок с маркерами живёт сразу после шапки, поэтому его видно при каждом открытии конспекта."""
    t = _topic(topic)
    p = _note(t)
    if not t or not p.exists():
        return "нет такого конспекта: %s\nначни: study_start topic=<имя> source=<что изучаем> why=<цель>" % p
    body = p.read_text(encoding="utf-8", errors="ignore")
    block = ("%s\n**Ход изучения:** просмотрено: %s · дальше: %s · _обновлено %s (%s)_\n%s\n"
             % (PROG_A, (done or "—").strip(), (next_step or "—").strip(), _now(), _who(), PROG_B))
    if PROG_A in body and PROG_B in body:
        i = body.find(PROG_A)
        j = body.find(PROG_B) + len(PROG_B)
        body = body[:i] + block.rstrip("\n") + body[j:]
    else:
        k = body.find("\n## ")
        body = (body[:k] + "\n" + block + body[k:]) if k > 0 else (body.rstrip("\n") + "\n\n" + block)
    p.write_text(body, encoding="utf-8")
    log("study: %s — ход изучения обновлён" % t)
    return "Ход изучения: просмотрено %s · дальше %s\n%s" % (done or "—", next_step or "—", p)


def _one_status(p):
    body = p.read_text(encoding="utf-8", errors="ignore")
    chunks = re.findall(r"^## (\d+)\. (.*)$", body, re.M)
    fails = len(re.findall(r"^### ❌ \d+\.", body, re.M))
    cand = len(re.findall(r"^- .+ · (?:замысел|черновик|готов) ·", body, re.M))
    prog = ""
    m = re.search(r"\*\*Ход изучения:\*\* (.*)", body)
    if m:
        prog = re.sub(r"\s*·\s*_обновлено.*", "", m.group(1)).strip()
    last = chunks[-1][1] if chunks else "—"
    mt = datetime.datetime.fromtimestamp(p.stat().st_mtime).strftime("%d.%m.%Y %H:%M")
    return ("  %-26s кусков %-4d неудач %-3d последний: %s\n"
            "     кандидатов в скиллы: %d, правлено %s\n     ход: %s\n     %s"
            % (p.parent.name, len(chunks), fails, last[:50], cand, mt, prog or "—", p))


def _backlog_lines():
    if not BACKLOG.exists():
        return []
    lines = BACKLOG.read_text(encoding="utf-8", errors="ignore").splitlines()
    i = next((k for k, l in enumerate(lines) if l.startswith(HEAD)), None)
    if i is None:
        return []
    j = next((k for k in range(i + 1, len(lines)) if lines[k].startswith("## ")), len(lines))
    return [l for l in lines[i + 1:j] if l.strip().startswith("- ")]


def study_status(topic="", **kw):
    """Что изучено: конспекты, где остановился, какие заготовки скиллов ждут."""
    t = _topic(topic)
    if t:
        p = _note(t)
        if not p.exists():
            return "конспекта нет: %s" % p
        rows = [_one_status(p)]
    else:
        # конспекты ищем в обоих местах: repo\ИЗУЧЕНО (правило с 24.09) и ИЗУЧИТЬ\ (старые темы)
        rows = []
        for root in (STUDY_ROOT, SRC_ROOT):
            if not root.exists():
                continue
            rows += [_one_status(d / "STUDY_NOTES.md") for d in sorted(root.iterdir())
                     if d.is_dir() and (d / "STUDY_NOTES.md").exists()]
    if not rows:
        rows = ["  конспектов нет — начни: study_start topic=<имя> source=<что изучаем> why=<цель>"]
    bl = _backlog_lines()
    return ("КОНСПЕКТЫ (%d):\n%s\n\nЗАГОТОВКИ СКИЛЛОВ (%d):\n%s"
            % (len(rows), "\n".join(rows), len(bl),
               "\n".join(bl) if bl else "  пусто — прикидывай скиллы по ходу изучения (study_skill)"))


TOOLS = [
    {"name": "study_start",
     "desc": "Завести конспект изучения (D:\\AI\\ИЗУЧИТЬ\\<тема>\\STUDY_NOTES.md): метод «изучил кусок — записал»",
     "params": {"topic": "имя темы", "source": "что изучаем (папка/файл/документ)", "why": "зачем изучаем"},
     "approval": False, "fn": study_start},
    {"name": "study_note",
     "desc": "Записать прочитанный кусок в конспект (запись ДО следующего куска) и сразу решить: нужен ли скилл?",
     "params": {"topic": "имя темы", "chunk": "что читал (файл/страницы/раздел)",
                "text": "что понял и что осталось", "skill": "имя скилла, если понял, что нужен"},
     "approval": False, "fn": study_note},
    {"name": "study_skill",
     "desc": "Прикинуть будущий скилл: заготовка в repo\\BACKLOG_tools.md со статусом замысел/черновик/готов",
     "params": {"skill": "имя скилла", "why": "почему нужен", "ready": "замысел|черновик|готов",
                "topic": "из какого конспекта"},
     "approval": True, "fn": study_skill},
    {"name": "study_fail",
     "desc": "ЗАПИСАТЬ НЕУДАЧУ СРАЗУ: выбран не тот инструмент, вылет, ошибка, пустой ответ — в раздел «ЧТО НЕ ПОЛУЧИЛОСЬ»",
     "params": {"topic": "имя темы", "what": "что делал", "tool": "какой инструмент выбрал",
                "result": "чем кончилось (вылет/ошибка/пусто)", "fix": "вывод и что делать в следующий раз",
                "skill": "если из этого нужен скилл — его имя"},
     "approval": False, "fn": study_fail},
    {"name": "study_progress",
     "desc": "Ход изучения: что просмотрено, что дальше (метод «файл за файлом, папка за папкой»)",
     "params": {"topic": "имя темы", "done": "что уже просмотрено", "next_step": "что дальше"},
     "approval": False, "fn": study_progress},
    {"name": "study_status",
     "desc": "Что изучено: конспекты, где остановился, сколько неудач, какие заготовки скиллов ждут",
     "params": {"topic": "одна тема (пусто = все)"}, "approval": False, "fn": study_status},
]