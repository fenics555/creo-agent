# -*- coding: utf-8 -*-
r"""
АГЕНТ v12 — БЛОК ДИАГНОСТИКИ v2 (diagnostic_tools.py)
Полная самопроверка: статика (синтаксис/импорты/дубли) + живой прогон
ВСЕХ читающих инструментов + сценарии из нескольких команд + щит + инфраструктура.
Запуск: python diagnostic_tools.py | в панели: diag_run / diag_test.
"""
import ast, builtins, json, socket, subprocess, urllib.request
from pathlib import Path
import core
import settings

HERE = Path(__file__).parent
CORE_FILES = ["core.py", "settings.py", "scanner.py", "users.py",
              "tools_registry.py", "panel.py", "agent.py"]

# инструменты, которые БЕЗОПАСНО дёргать без согласования
SAFE_CALLS = [
    ("creo_status", {}), ("creo_pwd", {}), ("creo_session", {}),
    ("creo_list_files", {"mask": "*.prt.*"}), ("creo_get_active", {}),
    ("search_kb", {"query": "пружина"}), ("index_state", {}),
    ("fleet_status", {}), ("one_c_status", {}), ("settings_show", {}),
    ("users_list", {}), ("strategy_read", {}), ("history_search", {"query": "трейл"}),
    ("passport_show", {}), ("trail_problems", {}), ("trail_trend", {}),
    ("proven_show", {}), ("fav_show", {}), ("self_check_note", {}),
]

def _ok(b): return "✓" if b else "✗"

# ---------- 1. СТАТИКА: синтаксис, импорты, дубли ----------
def check_files():
    out, seen, bad, n = [], {}, 0, 0
    for p in sorted(HERE.glob("*.py")):
        n += 1
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"), str(p))
        except SyntaxError as e:
            out.append("✗ %s — синтаксис, строка %s: %s" % (p.name, e.lineno, e.msg)); bad += 1; continue
        defined, used = set(), set()
        for x in ast.walk(tree):
            if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)): defined.add(x.name)
            elif isinstance(x, ast.arg): defined.add(x.arg)
            elif isinstance(x, ast.Name): (defined if isinstance(x.ctx, ast.Store) else used).add(x.id)
            elif isinstance(x, (ast.Import, ast.ImportFrom)):
                for a in x.names: defined.add((a.asname or a.name).split(".")[0])
            elif isinstance(x, ast.ExceptHandler) and x.name: defined.add(x.name)
        miss = sorted(u for u in used if u not in defined and u not in dir(builtins) and not u.startswith("__"))
        if miss: out.append("✗ %s — без импорта: %s" % (p.name, ", ".join(miss))); bad += 1
        for x in ast.walk(tree):
            if isinstance(x, ast.Assign):
                for t in x.targets:
                    if isinstance(t, ast.Name) and t.id == "TOOLS" and isinstance(x.value, ast.List):
                        for el in x.value.elts:
                            if isinstance(el, ast.Dict):
                                for k, v in zip(el.keys, el.values):
                                    if isinstance(k, ast.Constant) and k.value == "name" and isinstance(v, ast.Constant):
                                        if v.value in seen: out.append("✗ дубль инструмента %s: %s и %s" % (v.value, seen[v.value], p.name)); bad += 1
                                        else: seen[v.value] = p.name
    if not bad: out.insert(0, "✓ статика: %d .py, синтаксис/импорты/дубли ок" % n)
    return out

# ---------- 2. РЕЕСТР И ЩИТ ----------
def check_registry():
    import tools_registry as TR
    out = ["✓ реестр: блоков %d, инструментов %d" % (len(TR.BLOCKS), len(TR.TOOLS))]
    loaded = set(TR.BLOCKS)
    for p in HERE.glob("*_tools.py"):
        if p.stem not in loaded: out.append("✗ блок %s НЕ загружен реестром" % p.stem)
    names = [t["name"] for t in TR.TOOLS]
    for d in set(x for x in names if names.count(x) > 1): out.append("✗ дубль в реестре: %s" % d)
    wr = [t["name"] for t in TR.TOOLS if t.get("approval")]
    out.append("%s щит: %d пишущих под согласованием" % (_ok(len(wr) > 0), len(wr)))
    return out

# ---------- 3. OLLAMA / CREOSON / АГЕНТ ----------
def check_ollama():
    try:
        j = json.load(urllib.request.urlopen(core.OLL + "/api/tags", timeout=5))
        names = [m.get("name", "") for m in j.get("models", [])]
        cur = settings.get("llm_model") or ""
        out = ["✓ Ollama жива, моделей %d; чат-модель %s %s" % (
            len(names), cur, "на месте" if any(x.startswith(cur) for x in names) else "— НЕ НАЙДЕНА")]
        if not any(x.startswith("nomic-embed-text") for x in names): out.append("✗ нет nomic-embed-text")
        return out
    except Exception as e:
        return ["✗ Ollama недоступна: %s" % e]

def check_creoson():
    port_up = False
    try:
        s = socket.create_connection(("127.0.0.1", 8080), timeout=2); s.close(); port_up = True
    except Exception:
        pass
    if not port_up:
        out = ["✗ CREOSON: порт 8080 молчит. Лечение: CREO-START.bat (дебаг-клик)"]
        try:
            tl = subprocess.run(["tasklist", "/FO", "CSV"], capture_output=True, text=True, timeout=10).stdout.lower()
            out.append("%s процесс java %s" % (_ok("java" in tl), "жив" if "java" in tl else "мёртв"))
            out.append("%s процесс parametric.exe %s" % (_ok("parametric.exe" in tl), "жив" if "parametric.exe" in tl else "мёртв"))
        except Exception:
            pass
        return out
    try:
        r = urllib.request.Request("http://127.0.0.1:8080/creoson", json.dumps(
            {"command": "connection", "function": "is_creo_running", "data": {}}).encode(),
            {"Content-Type": "application/json"})
        j = json.load(urllib.request.urlopen(r, timeout=5))
        return ["✓ CREOSON жив; Creo запущен: %s" % ("ДА" if (j.get("data") or {}).get("running") else "НЕТ")]
    except Exception as e:
        return ["✗ порт 8080 открыт, но CREOSON не отвечает: %s" % e]

def check_agent():
    out = []
    for path in ("/status", "/panel", "/log"):
        try:
            urllib.request.urlopen("http://127.0.0.1:%d%s" % (8765, path), timeout=5)
            out.append("✓ эндпоинт %s отвечает" % path)
        except Exception as e:
            out.append("✗ эндпоинт %s: %s" % (path, e))
    try:
        import panel
        b = panel.build()
        out.append("✓ панель: секций %d, чипов %d, кнопок %d" % (len(b["groups"]), len(b["chips"]), len(b["actions"])))
        src = (HERE / "agent.py").read_text(encoding="utf-8", errors="ignore")
        for a in b["actions"]:
            if ('"%s"' % a["endpoint"]) not in src and ("'%s'" % a["endpoint"]) not in src:
                out.append("✗ кнопка «%s» бьёт в несуществующий %s" % (a["label"], a["endpoint"]))
    except Exception as e:
        out.append("✗ панель: %s" % e)
    return out

# ---------- 4. БАЗА, КОНФИГ, ИНФРА ----------
def check_kb():
    out = []
    c = core.db()
    try:
        nf = c.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        nc = c.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        nm = c.execute("SELECT COUNT(*) FROM models").fetchone()[0]
        out.append("✓ база: файлов %d, чанков %d, 3D-моделей %d" % (nf, nc, nm))
        if nc == 0: out.append("✗ чанков 0 — поиск не работает")
    except Exception as e:
        out.append("✗ база: %s" % e)
    finally:
        c.close()
    return out

def check_infra():
    out = []
    std = Path(r"Z:\PTC\CREO-START\START-STD")
    for f in ("CREO-START.bat", "CREO-START.vbs", "config.pro"):
        out.append("%s START-STD/%s" % (_ok((std / f).exists()), f))
    cc = (core.REPO / "SKILL_creoson_complete.md").exists() or (core.REPO / "Creo" / "SKILL_creoson_complete.md").exists()
    out.append("%s SKILL_creoson_complete.md (корень или Creo/)" % _ok(cc))
    return out

# ---------- 5. ЖИВОЙ ПРОГОН ИНСТРУМЕНТОВ ----------
def check_tools_live():
    import tools_registry as TR
    out, ok_n = ["— живой прогон читающих инструментов —"], 0
    for name, args in SAFE_CALLS:
        t = TR.get(name)
        if not t: continue  # note-заглушка не в реестре — пропускаем
        try:
            r = str(t["fn"](**args))
            if not r.strip(): out.append("✗ %s — пустой ответ" % name)
            elif r.startswith("ошибка исполнения"): out.append("✗ %s — %s" % (name, r[:80]))
            else:
                ok_n += 1
                out.append("✓ %s → %s" % (name, r[:60].replace("\n", " ")))
        except Exception as e:
            out.append("✗ %s — исключение: %s" % (name, e))
    out.append("прогон: %d инструментов ответили живыми данными" % ok_n)
    return out

# ---------- 6. СЦЕНАРИИ ИЗ НЕСКОЛЬКИХ КОМАНД ----------
def check_scenarios():
    import tools_registry as TR
    out = ["— сценарии из нескольких команд —"]
    try:
        pwd = str(TR.get("creo_pwd")["fn"]())
        fl = str(TR.get("creo_list_files")["fn"](mask="*.prt.*"))
        good = ("не узнал" not in pwd)
        out.append("%s «папка→файлы»: %s | строк файлов: %d" % (_ok(good), pwd[:45], len([x for x in fl.splitlines() if x.strip()])))
    except Exception as e:
        out.append("✗ «папка→файлы»: %s" % e)
    try:
        s = str(TR.get("search_kb")["fn"](query="пружина сжатия"))
        out.append("%s «поиск по БЗ»: фрагментов %d" % (_ok("[" in s), s.count("[")))
    except Exception as e:
        out.append("✗ «поиск по БЗ»: %s" % e)
    try:
        st = str(TR.get("creo_status")["fn"]())
        t = TR.get("creo_get_mass")
        ms = str(t["fn"]()) if (t and "ДА" in st) else "Creo не запущен — пропуск"
        good = ("ошибка" not in ms) and ("пропуск" not in ms)
        out.append("%s «статус→масса»: %s | %s" % (_ok(good), st[:40], ms[:40]))
    except Exception as e:
        out.append("✗ «статус→масса»: %s" % e)
    return out

def tool_test(**kw):
    out = ["🧪 ЖИВОЙ ПРОГОН:"]
    out += check_tools_live() + check_scenarios()
    out.append("ИТОГО красных: %d" % sum(1 for l in out if l.startswith("✗")))
    return "\n".join(out)

def tool_diag(**kw):
    out = ["🩺 САМОДИАГНОСТИКА ПОЛНАЯ:"]
    for fn in (check_files, check_registry, check_ollama, check_creoson, check_agent,
               check_kb, check_infra, check_tools_live, check_scenarios):
        try:
            out += fn()
        except Exception as e:
            out.append("✗ сбой проверки %s: %s" % (fn.__name__, e))
    out.append("ИТОГО проблем: %d" % sum(1 for l in out if l.startswith("✗")))
    return "\n".join(out)

TOOLS = [
    {"name": "diag_run", "desc": "Полная самодиагностика: статика, реестр, Ollama, CREOSON, кнопки, база, живой прогон, сценарии", "params": {}, "approval": False, "fn": tool_diag},
    {"name": "diag_test", "desc": "Только живой прогон инструментов и сценариев (быстро)", "params": {}, "approval": False, "fn": tool_test},
]

if __name__ == "__main__":
    import sys
    try:
        print(tool_diag(), flush=True)
    except Exception as e:
        print("ДИАГНОСТИКА УПАЛА: %r" % e, flush=True)
        sys.exit(1)