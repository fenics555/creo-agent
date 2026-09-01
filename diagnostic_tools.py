# -*- coding: utf-8 -*-
# АГЕНТ v12 — ЕДИНЫЙ БЛОК ДИАГНОСТИКИ (probe_tools поглощён и удалён).
# Семантика: шаг с ошибкой = НЕ ПРОЙДЕН; в конце каждого теста — вердикт.
# Полный лог запросов/ответов: diag_full.log; креосон-цикл дублируется в diag_creoson.log.
import ast, json, re, time, socket, urllib.request, traceback
from pathlib import Path
import core
from core import log, trace
import settings
import tools_registry as TR
import creo_tools as CT

HERE = Path(__file__).parent
FULL_LOG = Path(core.BASE) / "diag_full.log"
CREO_LOG = Path(core.BASE) / "diag_creoson.log"

BAD = ("ошибка исполнения", "traceback", "недоступен", "исключение:", "не удалось", "failed", "молчит", "exception")

def _w(line, both=False):
    try:
        with open(FULL_LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%m-%d %H:%M:%S"), line))
        if both:
            with open(CREO_LOG, "a", encoding="utf-8") as f:
                f.write("%s %s\n" % (time.strftime("%m-%d %H:%M:%S"), line))
    except Exception:
        pass

def _bad(text):
    t = (text or "").lower()
    return any(b in t for b in BAD)

def _call(name, args=None):
    t = TR.get(name)
    if not t:
        return False, "нет инструмента в реестре"
    t0 = time.time()
    try:
        res = str(t["fn"](**(args or {})))
        okf = not _bad(res)
    except Exception as e:
        res = "исключение: %s" % e
        okf = False
    ms = int((time.time() - t0) * 1000)
    _w(">> %s %s -> %s (%dмс) %s" % (name, json.dumps(args or {}, ensure_ascii=False)[:100], "PASS" if okf else "FAIL", ms, res[:150].replace("\n", " ")))
    return okf, res

def _statics():
    errs = []
    for p in sorted(HERE.glob("*.py")):
        try:
            ast.parse(p.read_text(encoding="utf-8"), str(p))
        except Exception as e:
            errs.append("%s: %s" % (p.name, e))
    names = [t["name"] for t in TR.TOOLS]
    dups = sorted({n for n in names if names.count(n) > 1})
    return errs, dups

def _ollama():
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=5) as r:
            models = [m.get("name") for m in json.loads(r.read().decode()).get("models", [])]
        return models, settings.get("llm_model")
    except Exception as e:
        return None, str(e)

def _http(path):
    try:
        with urllib.request.urlopen("http://127.0.0.1:8765%s" % path, timeout=5) as r:
            return r.status
    except Exception:
        return 0

def _db():
    c = core.db(); n = {}
    for tab in ("files", "chunks", "models", "history"):
        try:
            n[tab] = c.execute("SELECT COUNT(*) FROM %s" % tab).fetchone()[0]
        except Exception:
            n[tab] = -1
    c.close(); return n

def _creo_matrix():
    act = CT.tool_get_active()
    if act.startswith("не знаю"):
        return [("file:get_active", False, act)]
    probes = [("creo", "pwd", {}), ("creo", "list_files", {"filename": "*"}), ("file", "list", {}),
              ("file", "exists", {"file": act}), ("file", "get_fileinfo", {"file": act}),
              ("file", "massprops", {"file": act}), ("file", "relations_get", {"file": act}),
              ("file", "open_errors", {"file": act}), ("parameter", "list", {"file": act}),
              ("parameter", "exists", {"file": act, "name": "ОБОЗНАЧЕНИЕ"}),
              ("dimension", "list", {"file": act}), ("feature", "list", {"file": act}),
              ("bom", "get_paths", {"file": act, "paths": False, "top_level": False, "exclude_inactive": True}),
              ("familytable", "list", {"file": act}), ("layer", "list", {"file": act}),
              ("note", "list", {"file": act}), ("view", "list", {"file": act}),
              ("geometry", "bound_box", {"file": act})]
    rows = []
    for cmd, fn, data in probes:
        _w(">> %s:%s %s" % (cmd, fn, json.dumps(data, ensure_ascii=False)[:100]), True)
        j = CT.creo_call(cmd, fn, data, 20)
        okf = CT.ok(j)
        _w("<< %s:%s %s" % (cmd, fn, "OK" if okf else "ERR " + str(CT.errmsg(j))[:80]), True)
        rows.append((cmd + ":" + fn, okf, "" if okf else str(CT.errmsg(j))[:60]))
    return rows

BLACK = {"creo_kill", "creo_stop", "creo_start", "creo_erase", "creo_save", "creo_regenerate",
         "creo_rename_model", "creo_purge_versions", "creo_print_pdf", "creo_mapkey", "creo_assemble",
         "creo_set_param", "creo_set_relations", "creo_set_units", "creo_backup", "creo_draw_regenerate",
         "copy_model", "spec_create_active", "model_learn", "backup_restore", "user_add", "user_role",
         "settings_set", "index_run", "scan_run", "usage_build", "save_skill",
         "diag_run", "diag_test", "probe_run", "creoson_full_test", "diag_learn"}

def tool_probe_run(**kw):
    out, fails = [], []
    for t in TR.TOOLS:
        n = t["name"]
        if t.get("approval") or n in BLACK:
            continue
        okf, res = _call(n, {})
        out.append("%s %s — %s" % ("PASS" if okf else "FAIL", n, res[:70].replace("\n", " ")))
        if not okf:
            fails.append(n)
    v = "ПРОЙДЕН" if not fails else "НЕ ПРОЙДЕН: %s" % ", ".join(fails)
    _w("== probe_run: инструментов %d, ошибок %d" % (len(out), len(fails)))
    return "автопрогон %d инструментов:\n%s\nвердикт: %s" % (len(out), "\n".join(out), v)

def tool_diag_test(**kw):
    out, fails = [], []
    rows = _creo_matrix()
    bad = [r[0] for r in rows if not r[1]]
    out.append("матрица CREOSON: чтений %d, ошибок %d" % (len(rows), len(bad)))
    fails += bad
    for n in ("creo_status", "models_stats", "settings_show", "users_list", "backup_list", "fleet_status", "index_state", "model_rules"):
        okf, res = _call(n, {})
        out.append("%s %s — %s" % ("PASS" if okf else "FAIL", n, res[:60].replace("\n", " ")))
        if not okf:
            fails.append(n)
    v = "ПРОЙДЕН" if not fails else "НЕ ПРОЙДЕН: %s" % ", ".join(fails)
    _w("== diag_test вердикт: %s" % v)
    return "\n".join(out) + "\nвердикт: %s\nлог: diag_full.log" % v

def tool_diag_run(**kw):
    out, fails = [], []
    _w("== diag_run старт ==")
    errs, dups = _statics()
    out.append("статика: .py %d, ошибок синтаксиса %d, дубли %s" % (len(list(HERE.glob("*.py"))), len(errs), dups or "нет"))
    fails += ["статика:" + e[:30] for e in errs] + (["дубли"] if dups else [])
    out.append("реестр: блоков %d, инструментов %d" % (len(TR.BLOCKS), len(TR.TOOLS)))
    models, cur = _ollama()
    if models is None:
        out.append("Ollama: недоступна (%s)" % cur); fails.append("ollama")
    else:
        good = cur in models
        out.append("Ollama: моделей %d, чат-модель %s %s" % (len(models), cur, "на месте" if good else "НЕТ в списке"))
        if not good:
            fails.append("llm_model")
    for pth in ("/status", "/panel", "/log"):
        st = _http(pth)
        out.append("эндпоинт %s: %s" % (pth, st))
        if st != 200:
            fails.append("http" + pth)
    n = _db()
    out.append("база: %s" % n)
    if n.get("models", 0) <= 0:
        fails.append("база models")
    rows = _creo_matrix()
    bad = [r[0] for r in rows if not r[1]]
    out.append("CREOSON: чтений %d, ошибок %d" % (len(rows), len(bad)))
    fails += bad
    pr = tool_probe_run()
    out.append("автопрогон: " + pr.splitlines()[-1])
    if "НЕ ПРОЙДЕН" in pr:
        fails.append("probe_run")
    v = "ПРОЙДЕН" if not fails else "НЕ ПРОЙДЕН (%d): %s" % (len(fails), ", ".join(fails)[:400])
    _w("== diag_run вердикт: %s" % v)
    return "\n".join(out) + "\nвердикт: %s\nполный лог: diag_full.log" % v

def tool_creoson_full_test(**kw):
    import os
    out, fails = [], []
    def rep(line, okf=True):
        out.append(line); _w(line, True)
        if not okf:
            fails.append(line[:60])
    act = CT.tool_get_active()
    rep("== старт, активная: %s ==" % act)
    if act.startswith("не знаю"):
        rep("FAIL: нет активной модели", False)
        return "\n".join(out)
    d = str(Path(core.BASE) / "diag_test"); os.makedirs(d, exist_ok=True)
    for r in _creo_matrix():
        rep("чтение %-22s %s" % (r[0], "OK" if r[1] else "ERR " + r[2]), r[1])
    jl = CT.creo_call("file", "list", {})
    lst = CT._flex_list(jl.get("data")) if CT.ok(jl) else []
    src = next((x for x in lst if x.lower().endswith(".prt")), "")
    if not src:
        rep("FAIL: нет .prt для копии", False)
    else:
        base = re.sub(r"\.prt(\.\d+)?$", "", src, flags=re.I)
        jb = CT.creo_call("file", "backup", {"file": src, "dirname": d, "target_dir": d}, 30)
        rep("запись backup %s: %s" % (src, "OK" if CT.ok(jb) else "ERR " + str(CT.errmsg(jb))[:60]), CT.ok(jb))
        jp0 = CT.creo_call("creo", "pwd", {})
        dd0 = jp0.get("data")
        orig = dd0.get("directory") if isinstance(dd0, dict) else str(dd0 or "")
        jcd = CT.creo_call("creo", "cd", {"dirname": d})
        rep("запись cd diag_test: %s" % ("OK" if CT.ok(jcd) else "ERR"), CT.ok(jcd))
        copy = "diagtest_%d" % int(time.time())
        cands = sorted(Path(d).glob(base + ".prt*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if cands:
            try:
                os.rename(cands[0], Path(d) / (copy + ".prt"))
            except Exception as e:
                rep("FAIL OS rename: %s" % e, False)
        jo = CT.creo_call("file", "open", {"file": copy + ".prt", "display": False}, 30)
        rep("запись open копии: %s" % ("OK" if CT.ok(jo) else "ERR " + str(CT.errmsg(jo))[:60]), CT.ok(jo))
        jps = CT.creo_call("parameter", "set", {"file": copy + ".prt", "name": "DIAG_TEST", "value": "full", "type": "STRING"}, 20)
        rep("запись parameter:set: %s" % ("OK" if CT.ok(jps) else "ERR"), CT.ok(jps))
        jrs = CT.creo_call("file", "relations_set", {"file": copy + ".prt", "relations": "DIAG_REL = 42"}, 20)
        rep("запись relations_set: %s" % ("OK" if CT.ok(jrs) else "ERR"), CT.ok(jrs))
        jrg = CT.creo_call("file", "regenerate", {"file": copy + ".prt"}, 30)
        rep("запись regenerate: %s" % ("OK" if CT.ok(jrg) else "ERR"), CT.ok(jrg))
        jpl = CT.creo_call("parameter", "list", {"file": copy + ".prt"}, 20)
        have = []
        if CT.ok(jpl):
            dd = jpl.get("data") or {}
            have = [p.get("name") for p in (dd.get("paramlist") or dd.get("param_list") or [])]
        rep("запись чтение обратно DIAG_TEST: %s" % ("DIAG_TEST" in have), "DIAG_TEST" in have)
        jsv0 = CT.creo_call("file", "save", {"file": copy + ".prt"}, 20)
        rep("запись save ДО rename: %s" % ("OK" if CT.ok(jsv0) else "ERR"), CT.ok(jsv0))
        # save до rename (фикс General Error)
        CT.creo_call("file", "save", {"file": copy + ".prt"}, 20)
        jrn = CT.creo_call("file", "rename", {"file": copy + ".prt", "new_name": copy + "_ren"}, 20)
        rep("запись rename копии: %s" % ("OK" if CT.ok(jrn) else "ERR " + str(CT.errmsg(jrn))[:60]), CT.ok(jrn))
        cur = (copy + "_ren") if CT.ok(jrn) else copy
        jsv = CT.creo_call("file", "save", {"file": cur + ".prt"}, 20)
        rep("запись save: %s" % ("OK" if CT.ok(jsv) else "ERR"), CT.ok(jsv))
        je = CT.creo_call("file", "erase", {"file": cur + ".prt"}, 20)
        rep("запись erase: %s" % ("OK" if CT.ok(je) else "ERR"), CT.ok(je))
        CT.creo_call("creo", "cd", {"dirname": orig})
        for p in list(Path(d).glob("diagtest_*")) + list(Path(d).glob(base + ".prt*")):
            try:
                p.unlink(); _w("очистка del %s" % p.name, True)
            except Exception:
                pass
    v = "ПРОЙДЕН" if not fails else "НЕ ПРОЙДЕН (%d): %s" % (len(fails), "; ".join(fails)[:300])
    _w("== creoson_full_test вердикт: %s" % v, True)
    return "\n".join(out) + "\nвердикт: %s" % v

def tool_diag_learn(**kw):
    out = []
    t = TR.get("model_learn"); tr = TR.get("model_rules")
    if not t or not tr:
        return "FAIL: нет model_learn/model_rules в реестре"
    try:
        r1 = str(t["fn"]())
        out.append("model_learn: %s" % r1[:200])
    except Exception as e:
        tb = traceback.format_exc().replace("\n", " | ")
        _w("FAIL diag_learn: %s" % tb[:600])
        return "model_learn НЕ ПРОЙДЕН: %s\n%s" % (e, tb[-800:])
    try:
        r2 = str(tr["fn"]())
        out.append("model_rules: %s" % r2[:200])
    except Exception as e:
        return "\n".join(out) + "\nmodel_rules НЕ ПРОЙДЕН: %s" % e
    okf = not _bad(r1) and not _bad(r2)
    _w("== diag_learn: %s" % ("PASS" if okf else "FAIL"))
    return "\n".join(out) + "\nвердикт: %s" % ("ПРОЙДЕН" if okf else "НЕ ПРОЙДЕН")

TOOLS = [
    {"name": "diag_run", "desc": "Полная самодиагностика: статика, реестр, Ollama, эндпоинты, база, CREOSON, автопрогон; лог diag_full.log; вердикт", "params": {}, "approval": False, "fn": tool_diag_run},
    {"name": "diag_test", "desc": "Быстро: матрица CREOSON + ключевые живые инструменты; вердикт", "params": {}, "approval": False, "fn": tool_diag_test},
    {"name": "probe_run", "desc": "Автопрогон всех инструментов всех блоков (только чтение, без щита), каждый PASS/FAIL", "params": {}, "approval": False, "fn": tool_probe_run},
    {"name": "creoson_full_test", "desc": "CREOSON: чтения + пишущий цикл на копии (save ДО rename); любая ошибка = НЕ ПРОЙДЕН", "params": {}, "approval": True, "fn": tool_creoson_full_test},
    {"name": "diag_learn", "desc": "Тест обучения: model_learn + model_rules на активной модели, с traceback", "params": {}, "approval": True, "fn": tool_diag_learn},
]
