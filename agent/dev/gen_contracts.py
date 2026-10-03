# -*- coding: utf-8 -*-
"""gen_contracts.py — ГЕНЕРАТОР КОНТРАКТОВ `tool.json` для программ дома.

Зачем: волна 2 дала контракт, но переведены были 2 программы из 16. Остальные описаны
в `data\programs.json` (id, название, класс, окно, журнал) — этого достаточно, чтобы
собрать контракт, а остальное программа должна рассказать о себе сама (что есть на диске).

ПРАВИЛО ГЕНЕРАТОРА (важно): он **не выдумывает**. Всё, чего нельзя прочитать с диска или
из programs.json, ставится как ноль/пусто и помечается в `notes`. Класс Р (только чтение)
определяется по букве `klass` из programs.json: Р — читает, Ж — работает с Creo.

Запуск (посмотреть, что будет записано, без записи):
    python dev\gen_contracts.py
Запуск (записать недостающие):
    python dev\gen_contracts.py --write
"""
import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))
import tool_contract as TC  # noqa: E402

PROGJ = AGENT / "data" / "programs.json"
# Папки, которые не являются программами.
SKIP = {"dev", "TEST", "qa", "_disabled", "_legacy", "data", "__pycache__"}


def guess_engine(prog_dir, pid):
    """Движок — одноимённый .py или .bat. Ничего не выдумываем: что нет, то пусто."""
    for name in ("%s.py" % pid, "%s.bat" % pid):
        if (prog_dir / name).exists():
            return name
    pys = sorted(p.name for p in prog_dir.glob("*.py")
                 if not p.name.startswith("_"))
    return pys[0] if pys else ""


def guess_gui(prog_dir, pid):
    """Окно — gui.py или одноимённый *_gui.bat."""
    if (prog_dir / "gui.py").exists():
        return "gui.py"
    for p in sorted(prog_dir.glob("*_gui.bat")):
        return p.name
    for p in sorted(prog_dir.glob("*gui*.bat")):
        return p.name
    return ""


def guess_deps(prog_dir):
    """Зависимости: какие модули агента программа импортирует напрямую.

    Считается по коду (ast), а не по глазам: модуль называется так же, как файл."""
    import ast
    mods = set()
    for py in sorted(prog_dir.glob("*.py")):
        if py.name.startswith("_"):
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods.add(node.module.split(".")[0])
    known = [m for m in sorted(mods)
             if (AGENT / ("%s.py" % m)).exists() and m != py.name]
    return known


def guess_settings(prog_dir, pid):
    """Настройки — файл `<ид>_settings.json` в data\\ или рядом с программой."""
    p = AGENT / "data" / ("%s_settings.json" % pid)
    if p.exists():
        return p.name
    for pat in ("*settings*.json", "gui_settings.json"):
        for f in prog_dir.glob(pat):
            return f.name
    return ""


def build(prog, prog_dir):
    pid = prog["id"]
    c = {"id": pid, "title": prog.get("title") or pid, "version": 1,
         "kind": "act", "group": prog.get("group") or "общее",
         "needs_creo": prog.get("klass") == "Ж", "class": prog.get("klass") or "Р",
         "engine": guess_engine(prog_dir, pid),
         "gui": guess_gui(prog_dir, pid),
         "gui_bat": prog.get("window") or "",
         "readme": "README.md" if (prog_dir / "README.md").exists() else "",
         "cli": [], "inputs": [], "outputs": {"report": "", "log": prog.get("logs") or ""},
         "settings": guess_settings(prog_dir, pid),
         "deps": guess_deps(prog_dir), "approval": False}
    if c["gui"]:
        c["ui"] = "ui_common"
    notes = ["Сгенерировано gen_contracts.py из programs.json и состава папки; проверить глазами."]
    if not c["engine"]:
        notes.append("движок не найден — заполнить.")
    if not c["readme"]:
        notes.append("README нет — заполнить или создать.")
    if not c["inputs"]:
        notes.append("входы не описаны — заполнить.")
    c["notes"] = " ".join(notes)
    return c


def main(argv):
    write = "--write" in argv
    doc = json.loads(PROGJ.read_text(encoding="utf-8"))
    made, skipped = [], []
    for prog in doc.get("programs") or []:
        pid = prog["id"]
        if pid in SKIP:
            skipped.append(pid)
            continue
        pdir = AGENT / (prog.get("cwd") or pid)
        if not pdir.is_dir():
            skipped.append(pid)
            continue
        # Записи витрины про сам агент (cwd = "." или корень агента) — это НЕ программы
        # в отдельной папке: контракт им не полагается (найдено генератором 03.10.2026).
        if pdir.resolve() == AGENT.resolve() or prog.get("cwd") in (".", "", None):
            skipped.append(pid)
            continue
        # программа должна иметь собственный одноимённый движок или bat
        if not ((pdir / ("%s.py" % pid)).exists() or (pdir / ("%s.bat" % pid)).exists()):
            skipped.append(pid)
            continue
        existing, err = TC.load_dir(pdir)
        if existing is not None and not err:
            skipped.append(pid)          # контракт уже есть и валиден — не трогаем
            continue
        c = build(prog, pdir)
        e = TC.validate(c)
        made.append((pid, c, e))
    print("ГЕНЕРАТОР КОНТРАКТОВ: новых %d, уже есть/пропущено %d (%s)"
          % (len(made), len(skipped), ", ".join(skipped)))
    for pid, c, e in made:
        print("  %-18s engine=%-24s gui=%-14s deps=%s%s"
              % (pid, c["engine"] or "—", c["gui"] or "—", ",".join(c["deps"]) or "—",
                 "  ⚠ " + "; ".join(e) if e else ""))
    if not made:
        print("писать нечего.")
        return 0
    if not write:
        print("\nЭто было бы записано. Повтори с --write, чтобы записать.")
        return 0
    for pid, c, e in made:
        TC.save(c, AGENT / (c["id"]) / "tool.json")
        print("  записан: %s/tool.json" % pid)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))