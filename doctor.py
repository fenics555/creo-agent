# -*- coding: utf-8 -*-
"""v14 FINAL_2: agent.py — полный стриминг + движок + UX + пер-юзер + v14."""
import re
from pathlib import Path
AG = Path(r"D:\AI\tools\agent")
ap = AG / "agent.py"; a = ap.read_text(encoding="utf-8"); ch = False

STREAM = '''
import urllib.request as _ur
LIVE_TOK = {}
_orig_core_post = core.post
def _stream_post(path, payload, *ar, **kw):
    push = getattr(threading.current_thread(), "_tokpush", None)
    if path != "/api/chat" or not push or not settings.get("stream_tokens"):
        return _orig_core_post(path, payload, *ar, **kw)
    payload = dict(payload); payload["stream"] = True
    parts = []; st = {"buf": "", "mode": None}; lj = {}
    req = _ur.Request(core.OLL + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try:
        with _ur.urlopen(req, timeout=600) as resp:
            for line in resp:
                line = line.strip()
                if not line: continue
                try: j = json.loads(line)
                except Exception: continue
                lj = j; t = (j.get("message") or {}).get("content") or ""
                if t:
                    parts.append(t)
                    if st["mode"] != "tool":
                        st["buf"] += t
                        if st["mode"] is None:
                            if len(st["buf"]) >= 6:
                                if st["buf"].lstrip().startswith("[TOOL"): st["mode"] = "tool"
                                else: st["mode"] = "ans"; push(st["buf"]); st["buf"] = ""
                        elif st["mode"] == "ans": push(st["buf"]); st["buf"] = ""
    except Exception:
        p2 = dict(payload); p2["stream"] = False; return _orig_core_post(path, p2, *ar, **kw)
    r = {"message": {"content": "".join(parts)}}
    for k in ("prompt_eval_count","eval_count","prompt_eval_duration","eval_duration"):
        if k in lj: r[k] = lj[k]
    return r
core.post = _stream_post
'''
if "LIVE_TOK = {}" not in a and "import settings" in a:
    a = a.replace("import settings", "import settings" + STREAM, 1); ch = True
if "LIVE = {}" not in a: a = a.replace("PENDING = {}", "PENDING = {}\nLIVE = {}", 1); ch = True
if "parse_qs" not in a: a = a.replace("from urllib.parse import urlparse", "from urllib.parse import urlparse, parse_qs", 1); ch = True
if 'settings.model_for("chat")' not in a: a = re.sub(r'settings\.get\("llm_model"\)\s*or\s*"deepseek-r1:14b"', 'settings.model_for("chat")', a); ch = True
if "LAST_META" not in a:
    a = a.replace("PENDING = {}", 'PENDING = {}\nLAST_META = {"p":0,"r":0}', 1)
    a = re.sub(r'(opts, steps_max = beh\(\))', r'\1\n    LAST_META.update(p=0, r=0)', a, count=1)
    a = re.sub(r'(kind, payload, args = parse_model\(raw\))', 'try: LAST_META["p"] += r.get("prompt_eval_count") or 0; LAST_META["r"] += r.get("eval_count") or 0\n    except Exception: pass\n    \\1', a, count=1)
    ch = True
if "_SYS_CACHE" not in a:
    a = a.replace("def build_system():", '_SYS_CACHE = {}\ndef build_system():\n    if _SYS_CACHE.get("v"): return _SYS_CACHE["v"]', 1); ch = True
if "def _log(line)" not in a:
    m = re.search(r'steps_log, last_res, sig_prev, invalid_cnt = \[\], *" *", *None, *0', a)
    if m: a = a[:m.end()] + "\n    def _log(line): steps_log.append(line); LIVE.setdefault(client, []).append(line)" + a[m.end():]; a = a.replace("steps_log.append(", "_log("); ch = True
if "from concurrent.futures" not in a: a = a.replace("import json, re, socket, threading, time, datetime", "import json, re, socket, threading, time, datetime\nfrom concurrent.futures import ThreadPoolExecutor", 1); ch = True
if "parallel_tools" not in a and "    t = TR.get(name)" in a:
    par = '''    if settings.get("parallel_tools"):
        others = []
        for m in re.finditer(r"\\[TOOL:\\s*([A-Za-z0-9_]+)\\s*\\]\\s*(\\{.*?\\})\\s*\\[/TOOL\\]", raw, re.S):
            try: aa = json.loads(m.group(2))
            except Exception: aa = {}
            tt = TR.get(m.group(1))
            if tt and not tt.get("approval"): others.append((m.group(1), aa))
        if len(others) > 1:
            def _one(oa):
                nn, aa2 = oa
                try: return "%s → %s" % (nn, str(TR.get(nn)["fn"](**aa2))[:600])
                except Exception as e: return "%s → ошибка: %s" % (nn, e)
            try:
                with ThreadPoolExecutor(max_workers=4) as ex: res = "\\n".join(ex.map(_one, others))
                _log("parallel[%d]: %s" % (len(others), ", ".join(o[0] for o in others)))
                last_res = res; sig_prev = sig
                messages.append({"role": "assistant", "content": raw}); messages.append({"role": "user", "content": "[РЕЗУЛЬТАТ parallel]: %s" % res[:4000]})
                continue
            except Exception: pass
    t = TR.get(name)'''
    a = a.replace("    t = TR.get(name)", par, 1); ch = True
if "_scheduler" not in a:
    sched = '''
def _scheduler():
    last_day = ""
    while True:
        try:
            now = datetime.datetime.now()
            if settings.get("night_enable"):
                hh = int(settings.get("night_hour") or 2); mm = int(settings.get("night_minute") or 0)
                if now.hour == hh and now.minute == mm and now.strftime("%Y-%m-%d") != last_day:
                    last_day = now.strftime("%Y-%m-%d")
                    for t in str(settings.get("night_tasks") or "scan,index,usage").split(","):
                        t = t.strip()
                        try:
                            if t == "scan": scanner.scan_models()
                            elif t == "index": scanner.index_all()
                            elif t == "usage":
                                import usage_tools; usage_tools.build_usage(True)
                            elif t == "git":
                                import sync_tools; sync_tools.tool_fleet_sync()
                        except Exception as e: log("night %s err: %s" % (t, e))
                    log("night run done")
        except Exception: pass
        time.sleep(30)
'''
    a = a.replace("def beh():", sched + "\ndef beh():", 1)
    a2, n = re.subn(r'(try:\n\s*ThreadingHTTPServer\(\(HOST, PORT\), Hd\)\.serve_forever\(\))', r'threading.Thread(target=_scheduler, daemon=True).start()\n    \\1', a, count=1)
    if n: a = a2; ch = True
m = re.search(r'(?m)^(\s*)r = run_loop\(messages, client', a)
if m and "LIVE_TOK[client] = []" not in a:
    ind = m.group(1)
    a = a[:m.start()] + (ind + "settings.CUR = cl\n" + ind + "LIVE_TOK[client] = []; LIVE[client] = []\n" + ind + "def _push(t): LIVE_TOK.setdefault(client, []).append(t)\n" + ind + "threading.current_thread()._tokpush = _push\n" + ind + "_ta = time.time()\n") + a[m.start():]
    a = re.sub(r'(r = run_loop\(messages, client[^\n]*\))', r'\1\n    if int(settings.get("log_mode") or 1) >= 1:\n        r.setdefault("log", []).append("⏱ %dмс · 🔢 %d ток · шагов: %d" % (int((time.time() - _ta) * 1000), LAST_META["p"] + LAST_META["r"], r.get("steps", 1)))', a, count=1)
    ch = True
if "/livetoks" not in a and "/fleet/info" in a:
    a = a.replace('elif p == "/fleet/info":', '''elif p == "/livetoks":
    _c = users.token_info(self.headers.get("X-Token") or ""); qs = parse_qs(urlparse(self.path).query)
    last = int((qs.get("last") or ["0"])[0]); toks = LIVE_TOK.get(_c["login"] if _c else "", [])
    self._j({"toks": toks[last:], "last": len(toks)})
elif p == "/livesteps":
    _c = users.token_info(self.headers.get("X-Token") or ""); qs = parse_qs(urlparse(self.path).query)
    last = int((qs.get("last") or ["0"])[0]); lines = LIVE.get(_c["login"] if _c else "", [])
    self._j({"lines": lines[last:], "last": len(lines)})
elif p == "/fleet/info":''', 1); ch = True
if "PERSONAL" not in a and 'elif p == "/setcfg":' in a:
    a = a.replace('elif p == "/setcfg":', '''elif p == "/setcfg":
    if (b.get("key") or "") in settings.PERSONAL_KEYS:
        settings.set_for(cl, b.get("key"), b.get("value")); self._j({"ok": True}); return''', 1); ch = True
if "<title>АГЕНТ v12</title>" in a: a = a.replace("<title>АГЕНТ v12</title>", "<title>АГЕНТ v14</title>", 1); ch = True
if "<b>АГЕНТ v12</b>" in a: a = a.replace("<b>АГЕНТ v12</b>", "<b>АГЕНТ v14</b>", 1); ch = True
if 'data-val="guide"' not in a and '<button data-act="showlog">' in a:
    a = a.replace('<button data-act="showlog">', '<button data-act="chip" data-val="guide">❓</button><button data-act="showlog">', 1); ch = True
if "seen_guide" not in a and "login.style.display='none';init()" in a:
    a = a.replace("login.style.display='none';init()", "login.style.display='none';init();if(!localStorage.getItem('seen_guide')){localStorage.setItem('seen_guide','1');setTimeout(function(){qinp.value='guide';send()},400)}", 1); ch = True
if "ST2=setInterval" not in a and "J('/ask',{token:TK,q:q,image:IMG}).then(function(r){if(sp)sp.style.display='none';" in a:
    a = a.replace("J('/ask',{token:TK,q:q,image:IMG}).then(function(r){if(sp)sp.style.display='none';",
        "var TKI=0,ST2=setInterval(function(){J('/livetoks?last='+TKI).then(function(g){(g.toks||[]).forEach(function(t){TKI++;var s=d.querySelector('.stream')||(function(){var e=document.createElement('div');e.className='stream';d.appendChild(e);return e})();s.textContent+=t;chat.scrollTop=chat.scrollHeight;});});},120);var LV=0,LT=setInterval(function(){J('/livesteps?last='+LV).then(function(g){(g.lines||[]).forEach(function(l){LV++;var lg=d.querySelector('.live')||(function(){var e=document.createElement('div');e.className='log live';d.appendChild(e);return e})();lg.textContent+='· '+l+'\\n';});});},700);J('/ask',{token:TK,q:q,image:IMG}).then(function(r){clearInterval(ST2);clearInterval(LT);if(sp)sp.style.display='none';", 1)
    a = a.replace(".catch(function(e){if(sp)sp.style.display='none';d.innerHTML='ошибка: '+esc(e)})", ".catch(function(e){clearInterval(ST2);clearInterval(LT);if(sp)sp.style.display='none';d.innerHTML='ошибка: '+esc(e)})", 1); ch = True
if ch: ap.write_text(a, encoding="utf-8"); print("[+] agent: полный пакет")
print("FINAL_2 ГОТОВО: .\\AI_RESTART.bat")