# -*- coding: utf-8 -*-
r"""audit_settings.py (Cline, 04.10.2026) — ЧЕСТНЫЙ аудит настроек агента.

Зачем он, если есть dead_settings.py: тот ищет настройку по ИМЕНИ в тексте файлов, а это
обманывает трижды.
  1) чтение через СБОРКУ имени (settings.model_for(role) -> "model_" + role) не видно вовсе;
  2) настройка, упомянутая в комментарии, выглядит живой;
  3) настройка, которую ПРОЧИТАЛИ и СРАЗУ ВЫБРОСИЛИ, выглядит живой.

Этот инструмент разбирает код через ast и для каждой настройки даёт:
  - где читается: файл:строка + имя функции;
  - читается ли в исполняемом пути агента или только в GUI/витрине;
  - не выбрасывается ли значение сразу после чтения;
  - кто ПИШЕТ настройку (set_val / авто-регистрация из config.json).

Запуск: cmd /c "python -X utf8 dev\audit_settings.py > out 2>&1"
"""
import ast
import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))
import settings as S  # noqa: E402

SKIP_DIRS = {"__pycache__", "data", "_legacy", "_disabled", "node_modules", ".git", "settings"}
SKIP_FILES = {"settings.py", "dead_settings.py", "audit_settings.py",
              "check_settings_types.py"}
GUI_HINT = ("gui", "panel", "wiz", "_win", "ui_", "harvest_gui", "purge_gui")


def is_gui(rel):
    low = str(rel).replace("\\", "/").lower()
    return any(h in low for h in GUI_HINT)


def func_of(tree):
    """Карта: номер строки -> имя функции/класса (для отчёта «где читается»)."""
    out = {}

    def walk(node, ctx):
        for ch in ast.iter_child_nodes(node):
            # ВНИМАНИЕ: iter_child_nodes отдаёт и узлы Store/Del — у них НЕТ lineno,
            # обращение к нему роняет весь аудит ( AttributeError: 'Store' object ).
            ln = getattr(ch, "lineno", None)
            name = ctx
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = ch.name
            if ln is not None:
                out[ln] = name or ctx
            walk(ch, name)
    walk(tree, "")
    return out


def scan_file(py):
    """Возвращает (reads, writes, dynamic) по одному файлу. reads: key -> [сведения]."""
    rel = py.relative_to(AGENT)
    try:
        tree = ast.parse(py.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        return {}, [], ["%s: РАЗБОР НЕ УДАЛСЯ: %s" % (rel, str(e)[:60])]
    parents = {}
    for node in ast.walk(tree):
        for ch in ast.iter_child_nodes(node):
            parents[ch] = node
    fmap = func_of(tree)
    reads, writes, dynamic = {}, [], []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if isinstance(fn, ast.Attribute) and fn.attr in ("set_val", "set"):
            if node.args and isinstance(node.args[0], ast.Constant) \
                    and isinstance(node.args[0].value, str):
                writes.append((node.args[0].value, "%s:%d" % (rel, node.lineno)))
            else:
                dynamic.append("%s:%d set_val(имя не литералом)" % (rel, node.lineno))
            continue
        if isinstance(fn, ast.Attribute) and fn.attr == "model_for":
            dynamic.append("%s:%d model_for(role) -> ключ собирается как model_+role" % (rel, node.lineno))
            continue
        is_get = (isinstance(fn, ast.Attribute) and fn.attr in ("get", "get_for")) or \
                 (isinstance(fn, ast.Name) and fn.id in ("get", "get_for"))
        if not is_get:
            continue
        if not node.args or not isinstance(node.args[0], ast.Constant) \
                or not isinstance(node.args[0].value, str):
            if node.args:
                dynamic.append("%s:%d get(<не литерал>)" % (rel, node.lineno))
            continue
        key = node.args[0].value
        par = parents.get(node)
        thrown = isinstance(par, ast.Expr)          # прочитали и сразу выбросили
        reads.setdefault(key, []).append({
            "where": "%s:%d" % (rel, node.lineno),
            "func": fmap.get(node.lineno) or "модуль",
            "gui": is_gui(rel),
            "thrown": thrown,
        })
    return reads, writes, dynamic


def main():
    all_reads, all_writes, dynamics = {}, {}, []
    for py in sorted(AGENT.rglob("*.py")):
        rel = py.relative_to(AGENT)
        if any(p in SKIP_DIRS for p in rel.parts) or py.name in SKIP_FILES:
            continue
        r, w, d = scan_file(py)
        for k, v in r.items():
            all_reads.setdefault(k, []).extend(v)
        for k, v in w:
            all_writes.setdefault(k, []).append(v)
        dynamics.extend(d)

    rows = []
    for space, key, name, typ, defl, desc, ui in S.REGISTRY:
        sites = all_reads.get(key, [])
        live = [s for s in sites if not s["gui"] and not s["thrown"]]
        gui_only = [s for s in sites if s["gui"]]
        thrown = [s for s in sites if s["thrown"]]
        if not sites:
            verdict, lvl = "МЁРТВАЯ: никто не читает", "C"
        elif live:
            verdict, lvl = "ЖИВАЯ: %d мест исполнения" % len(live), "A"
        elif gui_only:
            verdict, lvl = "ТОЛЬКО GUI: в ответе агента не участвует", "B"
        else:
            verdict, lvl = "ЧИТАЕТСЯ И ВЫБРАСЫВАЕТСЯ", "D"
        rows.append({"key": key, "space": space, "type": typ, "verdict": verdict, "level": lvl,
                     "live": len(live), "gui": len(gui_only), "thrown": len(thrown),
                     "where": [s["where"] for s in sites][:4],
                     "writers": all_writes.get(key, [])[:3]})

    order = {"C": 0, "D": 1, "B": 2, "A": 3}
    # ДИНАМИЧЕСКИЕ ключи — их не видно поиском по имени, и без поправки аудит врёт:
    #   model_<role>  читается через settings.model_for(role)  -> settings.py:165
    #   PERSONAL_KEYS (ui_layout, chat_mode) читается через get_for -> settings.py:174
    dyn = " ".join(dynamics)
    model_roles = ("index", "chat", "fast", "creo", "spec", "trail", "web", "audit")
    personal = list(getattr(S, "PERSONAL_KEYS", []))
    for r in rows:
        k = r["key"]
        if k.startswith("model_") and k.split("_", 1)[1] in model_roles:
            r["level"] = "A*"
            r["verdict"] = "ЖИВАЯ: читается через model_for(role) — ключ собирается в коде"
            r["where"] = ["settings.py:165 model_for"] + r["where"]
        elif k in personal:
            r["level"] = "A*"
            r["verdict"] = "ЖИВАЯ: ПЕРСОНАЛЬНАЯ (get_for по логину), не из config.json"
            r["where"] = ["settings.py:174 get_for"] + r["where"]
    rows.sort(key=lambda r: (order.get(r["level"], 0), r["space"], r["key"]))
    print("=" * 100)
    print("АУДИТ НАСТРОЕК: %d всего; A (работает) = %d, B (только GUI) = %d, "
          "C (мёртвая) = %d, D (читается и выбрасывается) = %d"
          % (len(rows), sum(1 for r in rows if r["level"] == "A"),
             sum(1 for r in rows if r["level"] == "B"),
             sum(1 for r in rows if r["level"] == "C"),
             sum(1 for r in rows if r["level"] == "D")))
    print("=" * 100)
    cur = None
    for r in rows:
        if r["space"] != cur:
            cur = r["space"]
            print("\n--- %s ---" % cur)
        print("  [%s] %-22s %-8s %s" % (r["level"], r["key"], r["type"], r["verdict"]))
        if r["where"]:
            print("        читается: %s" % ", ".join(r["where"]))
        if r["writers"]:
            print("        пишется:  %s" % ", ".join(r["writers"]))
    print("\nДИНАМИЧЕСКИЕ КЛЮЧИ (поиском по имени не видны):")
    for d in sorted(set(dynamics))[:20]:
        print("   %s" % d)
    out = Path(r"D:\AI\log\reports\settings_audit_cline.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"rows": rows, "dynamic": sorted(set(dynamics))},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print("\nJSON отчёта: %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())