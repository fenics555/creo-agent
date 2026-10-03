# -*- coding: utf-8 -*-
"""gen_registry.py — ГЕНЕРАТОР таблицы «Программы» в dev\\PROGRAM_REGISTRY.md (волна 11).

ЗАЧЕМ: таблица программ в реестре была рукописной и протухала (волны 6-8 добавили
`batch_params`, `drawing_audit`, `plan_run`, `rules` — их в таблице не было). Источник
правды о программе — её контракт `tool.json` (волна 2) плюс список витрины
`data\\programs.json`. Реестр собирается из них, а не пишется руками.

ЗАКОН ГЕНЕРАТОРА (как в gen_contracts.py): **не выдумывает**. Всё, чего нельзя прочитать
с диска или из programs.json, печатается как «—» и попадает в раздел расхождений.

ЧТО ПИШЕТ: только секцию между маркерами `<!-- REGISTRY:BEGIN -->` и `<!-- REGISTRY:END -->`.
Если маркеров нет, файл реестра не трогается и выводится стоп.

Запуск: `python dev\\gen_registry.py` — проба; с `--write` — запись в реестр.
"""
import io
import json
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))
import tool_contract as TC  # noqa: E402

PROGJ = AGENT / "data" / "programs.json"
REGISTRY = AGENT / "dev" / "PROGRAM_REGISTRY.md"
BEGIN = "<!-- REGISTRY:BEGIN -->"
END = "<!-- REGISTRY:END -->"
DASH = "—"


def _load_programs():
    """Список витрины. Не читается — честная пустая структура, программа не падает."""
    try:
        return json.loads(PROGJ.read_text(encoding="utf-8"))
    except Exception as e:
        return {"groups": [], "programs": [], "error": str(e)}


def _settings_of(pid, c, pd):
    """Настройки: сначала контракт, потом список витрины, потом — что есть на диске."""
    s = (c or {}).get("settings") or pd.get("settings") or ""
    if s:
        return "`%s`" % s
    found = sorted(p.name for p in (AGENT / pid).glob("*settings*.json"))
    return "`%s`" % found[0] if found else DASH


def _logs_of(pid, c, pd):
    """Журнал: контракт -> витрина -> наличие папки в log\\."""
    lg = ((c or {}).get("outputs") or {}).get("log") if c else ""
    lg = lg or pd.get("logs") or ""
    if lg:
        return "`%s`" % lg.replace("D:\\AI\\log\\", "").rstrip("\\")
    if (Path("D:/AI/log") / pid).is_dir():
        return "`%s\\`" % pid
    return "не завела"


def _row(pid, c, err, pd, pd_err):
    """Одна строка таблицы. Пустое значение — «—», а не выдумка."""
    title = (c or {}).get("title") or pd.get("title") or pid
    klass = (c or {}).get("class") or pd.get("klass") or DASH
    if (c or {}).get("needs_creo"):
        klass += " (нужен Creo)"
    bat = (c or {}).get("gui_bat") or pd.get("window") or ""
    win = "`%s`" % bat if bat else DASH
    cli = (c or {}).get("cli") or []
    eng = (c or {}).get("engine") or DASH
    drive = ("`%s` %s" % (eng, " ".join(cli))).strip() if cli else "`%s`" % eng
    flags = []
    if err:
        flags.append("контракт: %s" % err)
    if pd_err:
        flags.append("витрина: %s" % pd_err)
    if not c:
        if pd.get("contract"):
            flags.append("контракт не полагается — %s" % pd["contract"].split("(", 1)[-1].rstrip(")"))
        else:
            flags.append("контракта нет")
    if not pd.get("status"):
        flags.append("состояния нет")
    state = pd.get("status") or DASH
    if flags:
        state = "%s — %s" % (DASH if state == DASH else state, "; ".join(flags))
    if len(state) > 300:
        state = state[:297] + "..."
    readme = (c or {}).get("readme") or pd.get("readme") or ""
    tail = " · паспорт `%s`" % readme if readme else ""
    return ("| **%s** | %s | %s | %s | %s · %s | %s%s |"
            % (title, klass, win, drive, _logs_of(pid, c, pd),
               _settings_of(pid, c, pd), state, tail))



def build():
    """Собирает (текст секции, расхождения). Только чтение — записи на диске нет."""
    doc = _load_programs()
    groups = doc.get("groups") or []
    progs = {p["id"]: p for p in (doc.get("programs") or []) if p.get("id")}
    contracts = TC.all_contracts(AGENT)
    lines = ["## Сгенерированная таблица программ", "",
             "> Сгенерировано `dev\\gen_registry.py` из контрактов `tool.json` и списка витрины",
             "> `data\\programs.json` (%s). Руками таблицу не правят: правка источника и "
             "повторный прогон." % doc.get("updated", "?"),
             "> Контрактов: %d, программ в списке витрины: %d." % (len(contracts), len(progs)), ""]
    for g in groups:
        ids = [p["id"] for p in progs.values() if p.get("group") == g["id"]]
        ids += [pid for pid, v in contracts.items()
                if (v[0] or {}).get("group") == g["id"] and pid not in ids]
        if not ids:
            continue
        lines.append("### %s %s — %s" % (g.get("icon", ""), g.get("title", g["id"]),
                                         g.get("note", "")))
        lines += ["",
                  "| Программа | Класс | Вход (ОКНО) | Движок (ДВИЖОК) | Логи · настройки | Состояние |",
                  "|---|---|---|---|---|---|"]
        for pid in ids:
            c, _p, err = contracts.get(pid, (None, None, None))
            pd = progs.get(pid) or {"id": pid}
            lines.append(_row(pid, c, err, pd, doc.get("error")))
        lines.append("")
    mismatch = []
    for pid in sorted(set(contracts) | set(progs)):
        # запись может честно помечать «контракт не полагается» — это не расхождение
        opt_out = bool(progs.get(pid, {}).get("contract"))
        if pid not in contracts and not opt_out:
            mismatch.append("%s — есть в витрине, контракта tool.json нет" % pid)
        if pid not in progs:
            mismatch.append("%s — контракт есть, в списке витрины нет" % pid)
    if mismatch:
        lines += ["### Расхождения источников", ""] + ["* %s" % m for m in mismatch] + [""]
    return "\n".join(lines).rstrip() + "\n", mismatch



def main(argv):
    section, mismatch = build()
    print("СЕКЦИЯ (%d строк):" % len(section.splitlines()))
    print(section)
    print("РАСХОЖДЕНИЯ: %d" % len(mismatch))
    for m in mismatch:
        print("  ! %s" % m)
    if "--write" not in argv:
        print("\nЭто было бы записано. Повтори с --write, чтобы записать в реестр.")
        return 0
    txt = REGISTRY.read_text(encoding="utf-8")
    if BEGIN not in txt or END not in txt:
        print("СТОП: в реестре нет маркеров %s / %s — файл не тронут." % (BEGIN, END))
        return 2
    # замена через функцию: в секции есть «<!--», в шаблоне подстановки это сломало бы re
    new = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END),
                 lambda _m: BEGIN + "\n" + section + END, txt, flags=re.S)
    if new == txt:
        print("НЕТ СМЕНЫ: секция уже совпадает с источниками.")
        return 0
    REGISTRY.write_text(new, encoding="utf-8")
    print("ЗАПИСАНО: %s (%d символов)" % (REGISTRY, len(new)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

