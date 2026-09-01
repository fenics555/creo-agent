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

# ---- матрица CREOSON (поглощено из creoson_test.py) ----

# ==== CREOSON: ОДИН полный тест; всё в diag_creoson.log ====
import os as _os
import re as _re
import time as _time
import json as _json
from pathlib import Path as _Path
import creo_tools as CT

def _fw(line):
    try:
        with open(_Path(core.BASE) / "diag_creoson.log", "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_time.strftime("%m-%d %H:%M:%S"), line))
    except Exception:
        pass

if getattr(CT.creo_raw, "__name__", "") != "_logged_raw":
    _orig_raw = CT.creo_raw
    def _logged_raw(cmd, fn, data=None, t=15):
        _fw(">> %s:%s %s" % (cmd, fn, _json.dumps(data or {}, ensure_ascii=False)[:200]))
        j = _orig_raw(cmd, fn, data, t)
        _fw("<< %s:%s %s" % (cmd, fn, "OK" if CT.ok(j) else "ERR " + str(CT.errmsg(j))[:80]))
        return j
    CT.creo_raw = _logged_raw

def tool_creoson_full_test(**kw):
    out = ["ПОЛНЫЙ ТЕСТ CREOSON (чтение -> запись на копии -> очистка):"]
    def rep(line):
        out.append(line); _fw(line)
    act = CT.tool_get_active()
    rep("== старт, активная: %s ==" % act)
    reads = [
        ("creo", "pwd", {}), ("creo", "list_files", {"filename": "*"}),
        ("creo", "get_config", {"name": "trail_dir"}),
        ("file", "list", {}), ("file", "get_active", {}), ("file", "exists", {"file": act}),
        ("file", "get_fileinfo", {"file": act}), ("file", "massprops", {"file": act}),
        ("file", "relations_get", {"file": act}), ("file", "open_errors", {"file": act}),
        ("parameter", "list", {"file": act}), ("parameter", "exists", {"file": act, "name": "ОБОЗНАЧЕНИЕ"}),
        ("dimension", "list", {"file": act}), ("feature", "list", {"file": act}),
        ("bom", "get_paths", {"file": act, "paths": False, "top_level": False, "exclude_inactive": True}),
        ("familytable", "list", {"file": act}), ("layer", "list", {"file": act}),
        ("note", "list", {"file": act}), ("view", "list", {"file": act}),
        ("geometry", "bound_box", {"file": act}),
    ]
    for cmd, fn, data in reads:
        j = CT.creo_call(cmd, fn, data, 20)
        rep("чтение %-20s %s" % (cmd + ":" + fn, "OK" if CT.ok(j) else "ERR " + str(CT.errmsg(j))[:60]))
    d = str(_Path(core.BASE) / "diag_test"); _os.makedirs(d, exist_ok=True)
    src = act if act.lower().endswith(".prt") else ""
    if not src:
        jl = CT.creo_call("file", "list", {})
        src = next((x for x in CT._flex_list(jl.get("data")) if str(x).lower().endswith(".prt")), "")
    if not src:
        rep("запись: нет .prt для копии — цикл пропущен")
    else:
        base = _re.sub(r"\.prt(\.\d+)?$", "", src, flags=_re.I)
        jb = CT.creo_call("file", "backup", {"file": src, "dirname": d, "target_dir": d}, 30)
        rep("запись backup %s: %s" % (src, "OK" if CT.ok(jb) else "ERR " + str(CT.errmsg(jb))[:60]))
        cands = sorted(_Path(d).glob(base + ".prt*"), key=lambda q: q.stat().st_mtime, reverse=True)
        copy = "diagtest_%d" % int(_time.time())
        if cands:
            _os.rename(cands[0], _Path(d) / (copy + ".prt"))
        jp0 = CT.creo_call("creo", "pwd", {})
        dd0 = jp0.get("data")
        orig = (dd0.get("directory") if isinstance(dd0, dict) else str(dd0 or "")) or ""
        CT.creo_call("creo", "cd", {"dirname": d})
        jo = CT.creo_call("file", "open", {"file": copy + ".prt", "display": False}, 30)
        rep("запись open копии: %s" % ("OK" if CT.ok(jo) else "ERR " + str(CT.errmsg(jo))[:60]))
        jps = CT.creo_call("parameter", "set", {"file": copy + ".prt", "name": "DIAG_TEST", "value": "full", "type": "STRING"}, 20)
        rep("запись parameter:set: %s" % ("OK" if CT.ok(jps) else "ERR " + str(CT.errmsg(jps))[:60]))
        jrs = CT.creo_call("file", "relations_set", {"file": copy + ".prt", "relations": "DIAG_REL = 42"}, 20)
        rep("запись relations_set: %s" % ("OK" if CT.ok(jrs) else "ERR " + str(CT.errmsg(jrs))[:60]))
        jrg = CT.creo_call("file", "regenerate", {"file": copy + ".prt"}, 30)
        rep("запись regenerate: %s" % ("OK" if CT.ok(jrg) else "ERR " + str(CT.errmsg(jrg))[:60]))
        jpl = CT.creo_call("parameter", "list", {"file": copy + ".prt"}, 20)
        have = []
        if CT.ok(jpl):
            dd = jpl.get("data") or {}
            have = [q.get("name") for q in (dd.get("paramlist") or dd.get("param_list") or [])]
        rep("запись чтение обратно DIAG_TEST: %s" % ("DIAG_TEST" in have))
        jrn = CT.creo_call("file", "rename", {"file": copy + ".prt", "new_name": copy + "_ren"}, 20)
        rep("запись rename копии: %s" % ("OK" if CT.ok(jrn) else "ERR " + str(CT.errmsg(jrn))[:60]))
        cur = (copy + "_ren") if CT.ok(jrn) else copy
        jsv = CT.creo_call("file", "save", {"file": cur + ".prt"}, 20)
        rep("запись save: %s" % ("OK" if CT.ok(jsv) else "ERR " + str(CT.errmsg(jsv))[:60]))
        je = CT.creo_call("file", "erase", {"file": cur + ".prt"}, 20)
        rep("запись erase: %s" % ("OK" if CT.ok(je) else "ERR " + str(CT.errmsg(je))[:60]))
        if orig:
            CT.creo_call("creo", "cd", {"dirname": orig})
        for q in list(_Path(d).glob("diagtest_*")) + list(_Path(d).glob(base + ".prt*")):
            try:
                q.unlink(); _fw("очистка del %s" % q.name)
            except Exception:
                pass
    rep("== конец ==")
    out.append("полный лог (кто/когда/что): diag_creoson.log")
    return "\n".join(out)

TOOLS += [
    {"name": "creoson_full_test", "desc": "ОДИН полный тест CREOSON: 20 чтений + пишущий цикл на копии (backup, cd, open, параметр, relations, regenerate, rename, save, erase) + очистка. Всё в diag_creoson.log. Без параметров.", "params": {}, "approval": True, "fn": tool_creoson_full_test},
]
