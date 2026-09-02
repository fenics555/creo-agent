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
    wd0 = CT.tool_pwd()
    try:
        import os, re, time, pathlib
        out, fails = [], []
        def rep(line, okf=True):
            out.append(line); _w(line, True)
            if not okf: fails.append(line[:70])
        act = CT.tool_get_active()
        rep("== старт, активная: %s ==" % act)
        for cmd, fn, data in [("creo", "pwd", {}), ("creo", "list_files", {"filename": "*"}),
                ("file", "list", {}), ("file", "exists", {"file": act}),
                ("file", "get_fileinfo", {"file": act}), ("file", "massprops", {"file": act}),
                ("file", "relations_get", {"file": act}), ("file", "open_errors", {"file": act}),
                ("parameter", "list", {"file": act}), ("parameter", "exists", {"file": act, "name": "ОБОЗНАЧЕНИЕ"}),
                ("dimension", "list", {"file": act}), ("feature", "list", {"file": act}),
                ("bom", "get_paths", {"file": act, "paths": False, "top_level": False, "exclude_inactive": True}),
                ("familytable", "list", {"file": act}), ("layer", "list", {"file": act}),
                ("note", "list", {"file": act}), ("view", "list", {"file": act}),
                ("geometry", "bound_box", {"file": act})]:
            jz = CT.creo_call(cmd, fn, data, 20)
            rep("чтение %-20s %s" % (cmd + ":" + fn, "OK" if CT.ok(jz) else "ERR " + str(CT.errmsg(jz))[:50]), CT.ok(jz))
        dd0 = (CT.creo_call("creo", "pwd", {}) or {}).get("data")
        orig = (dd0.get("directory") if isinstance(dd0, dict) else str(dd0 or "")) or ""
        d = str(pathlib.Path(core.BASE) / "diag_test"); os.makedirs(d, exist_ok=True)
        jl = CT.creo_call("file", "list", {})
        lst = CT._flex_list(jl.get("data")) if CT.ok(jl) else []
        src = next((x for x in lst if x.lower().endswith(".prt")), "")
        if not src:
            rep("FAIL: нет .prt в сессии для копии", False)
        else:
            base = re.sub(r"\.prt(\.\d+)?$", "", src, flags=re.I)
            jb = CT.creo_call("file", "backup", {"file": src, "target_dir": d}, 30)
            rep("запись backup %s (target_dir): %s" % (src, "OK" if CT.ok(jb) else "ERR " + str(CT.errmsg(jb))[:60]), CT.ok(jb))
            jcd = CT.creo_call("creo", "cd", {"dirname": d})
            rep("запись cd diag_test: %s" % ("OK" if CT.ok(jcd) else "ERR " + str(CT.errmsg(jcd))[:50]), CT.ok(jcd))
            copy = "diagtest_%d" % int(time.time())
            cands = sorted(pathlib.Path(d).glob(base + ".prt*"), key=lambda q: q.stat().st_mtime, reverse=True)
            if cands:
                try:
                    os.rename(cands[0], pathlib.Path(d) / (copy + ".prt")); rep("запись ОС-rename бэкапа в копию: OK")
                except Exception as e:
                    rep("запись ОС-rename бэкапа: ERR %s" % e, False)
            else:
                rep("FAIL: бэкап не оставил файл в diag_test", False)
            jo = CT.creo_call("file", "open", {"file": copy + ".prt", "display": False}, 30)
            rep("запись open копии: %s" % ("OK" if CT.ok(jo) else "ERR " + str(CT.errmsg(jo))[:60]), CT.ok(jo))
            jps = CT.creo_call("parameter", "set", {"file": copy + ".prt", "name": "DIAG_TEST", "value": "full", "type": "STRING"}, 20)
            rep("запись parameter:set: %s" % ("OK" if CT.ok(jps) else "ERR " + str(CT.errmsg(jps))[:60]), CT.ok(jps))
            jrg = CT.creo_call("file", "regenerate", {"file": copy + ".prt"}, 30)
            rep("запись regenerate: %s" % ("OK" if CT.ok(jrg) else "ERR " + str(CT.errmsg(jrg))[:50]), CT.ok(jrg))
            jpl = CT.creo_call("parameter", "list", {"file": copy + ".prt"}, 20)
            have = []
            if CT.ok(jpl):
                dd = jpl.get("data") or {}
                have = [q2.get("name") for q2 in (dd.get("paramlist") or dd.get("param_list") or [])]
            rep("запись чтение обратно DIAG_TEST: %s" % ("DIAG_TEST" in have), "DIAG_TEST" in have)
            jsv = CT.creo_call("file", "save", {"file": copy + ".prt"}, 20)
            rep("запись save: %s" % ("OK" if CT.ok(jsv) else "ERR " + str(CT.errmsg(jsv))[:50]), CT.ok(jsv))
            je = CT.creo_call("file", "erase", {"file": copy + ".prt"}, 15)
            rep("запись erase: %s" % ("OK" if CT.ok(je) else "ERR " + str(CT.errmsg(je))[:50]), CT.ok(je))
            ren_ok = False
            for q3 in sorted(pathlib.Path(d).glob(copy + ".prt*"), key=lambda q: q.stat().st_mtime, reverse=True):
                try:
                    os.rename(q3, pathlib.Path(d) / (copy + "_ren.prt")); ren_ok = True; break
                except Exception:
                    pass
            rep("запись rename (ОС — правильно для async CREOSON): %s" % ("OK" if ren_ok else "ERR"), ren_ok)
            if orig:
                CT.creo_call("creo", "cd", {"dirname": orig})
            for q4 in list(pathlib.Path(d).glob("diagtest_*")) + list(pathlib.Path(d).glob(base + ".prt*")):
                try:
                    q4.unlink(); _w("очистка del %s" % q4.name, True)
                except Exception:
                    pass
        v = "ПРОЙДЕН" if not fails else "НЕ ПРОЙДЕН (%d): %s" % (len(fails), "; ".join(fails)[:300])
        _w("== creoson_full_test вердикт: %s" % v, True)
        return "\n".join(out) + "\nвердикт: %s" % v
    finally:
        if wd0: CT.creo_call("creo", "cd", {"dirname": wd0}, 15)

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


def tool_diag_usage(**kw):
    import core
    c = core.db()
    total = c.execute("SELECT COUNT(*) FROM usage").fetchone()[0]
    known = c.execute("SELECT COUNT(*) FROM usage WHERE child LIKE ? AND parent LIKE ?",
                      ("creoson_tests-01-1%", "creoson_tests-01.%")).fetchone()[0]
    c.close()
    prob = []
    if total == 0: prob.append("индекс пуст: 0 ссылок")
    if known == 0: prob.append("известный ответ не найден: creoson_tests-01-1 в creoson_tests-01")
    v = "ПРОЙДЕН" if not prob else "НЕ ПРОЙДЕН: " + "; ".join(prob)
    return "ссылок: %d, известная пара: %d -> %s" % (total, known, v)

TOOLS.append({"name": "diag_usage", "desc": "Семантический тест индекса «где используется»: ссылок>0 и известная пара на месте", "params": {}, "approval": False, "fn": tool_diag_usage})


import re as WR
import core as WC
import urllib.request as WU
def tool_diag_web(**kw):
    import settings
    out, fails = [], []
    for u in ["http://127.0.0.1:8765/status", str(settings.get("web_test_url") or "https://cccp3d.ru")]:
        try:
            r = WU.Request(u, headers={"User-Agent": "Mozilla/5.0 (agent)"})
            with WU.urlopen(r, timeout=10) as resp:
                st = getattr(resp, "status", 200)
                html = resp.read().decode(resp.headers.get_content_charset() or "utf-8", "ignore")
            t = WC.clean(html)
            fl = []
            if WR.search(r"captcha|бот|не робот|BotHunt", html, WR.I): fl.append("captcha")
            if len(t) < 200 and WR.search(r'id=["\']?(root|app|__next)', html, WR.I): fl.append("SPA")
            out.append("• %s -> %s | %d симв%s" % (u, st, len(t), (" | " + "; ".join(fl)) if fl else ""))
        except Exception as e:
            out.append("• %s -> ERR %s" % (u, str(e)[:60])); fails.append(u)
    return "\n".join(out) + "\nвердикт: %s" % ("ПРОЙДЕН" if not fails else "НЕ ПРОЙДЕН: " + ", ".join(fails))
TOOLS += [{"name": "diag_web", "desc": "Диагностика веб-стека: агент + внешний URL, детект SPA/captcha", "params": {}, "approval": False, "fn": tool_diag_web}]
