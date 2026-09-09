# -*- coding: utf-8 -*-
# DOCTOR v33 — живой стрим размышлений в вебе + ползунок num_ctx до 131072.
# 1) LIVE_THINK: канал мыслей параллельно LIVE_TOK.
# 2) _stream_post: куски message.thinking уходят в LIVE_THINK клиента.
# 3) ask(): сброс LIVE_THINK + метка клиента на потоке.
# 4) GET /livethink — эндпоинт опроса мыслей.
# 5) PAGE: третий интервал опроса, div мыслей создаётся при первом токене и печатается живо.
# 6) PAGE: блок размышлений раскрыт по умолчанию.
# 7) PAGE: таймаут fetch 300с -> 900с.
# 8) settings.py: диапазон num_ctx до 131072 (ползунок перестаёт врать).
import re
from pathlib import Path

AG = Path(r"D:\AI\tools\agent")
FAILS = []; SKIPS = []

def py_ok(t, n):
    try:
        compile(t, n, "exec"); return True
    except SyntaxError as e:
        print("[SYNTAX] %s: %s" % (n, e)); return False

a = (AG / "agent.py").read_text(encoding="utf-8")

ITEMS = [
    ("LIVE_THINK global",
     "LIVE_TOK = {}\n_orig_core_post = core.post",
     "LIVE_TOK = {}\nLIVE_THINK = {}\n_orig_core_post = core.post"),
    ("stream thinking push",
     '                tth = (j.get("message") or {}).get("thinking") or ""\n                if tth: thparts.append(tth)\n                if tth and not t:\n                    continue',
     '                tth = (j.get("message") or {}).get("thinking") or ""\n                if tth:\n                    thparts.append(tth)\n                    _tc = getattr(threading.current_thread(), "_tokclient", None)\n                    if _tc is not None:\n                        LIVE_THINK.setdefault(_tc, []).append(tth)\n                if tth and not t:\n                    continue'),
    ("ask reset + thread client",
     "    LIVE_TOK[client] = []\n    def _push(t): LIVE_TOK.setdefault(client, []).append(t)\n    threading.current_thread()._tokpush = _push",
     "    LIVE_TOK[client] = []\n    LIVE_THINK[client] = []\n    def _push(t): LIVE_TOK.setdefault(client, []).append(t)\n    threading.current_thread()._tokpush = _push\n    threading.current_thread()._tokclient = client"),
    ("GET /livethink",
     '            toks = LIVE_TOK.get(_cl6["login"] if _cl6 else "", [])\n            self._j({"toks": toks[last:], "last": len(toks)})',
     '            toks = LIVE_TOK.get(_cl6["login"] if _cl6 else "", [])\n            self._j({"toks": toks[last:], "last": len(toks)})\n        elif p == "/livethink":\n            _cl7 = users.token_info(self.headers.get("X-Token") or "")\n            qs7 = parse_qs(urlparse(self.path).query)\n            last7 = int((qs7.get("last") or ["0"])[0])\n            ths = LIVE_THINK.get(_cl7["login"] if _cl7 else "", [])\n            self._j({"toks": ths[last7:], "last": len(ths)})'),
    ("PAGE live think interval",
     "var LV=0,LT=setInterval(function(){J('/livesteps?last='+LV).then(function(g){(g.lines||[]).forEach(function(l){LV++;var lg=d.querySelector('.live')||(function(){var e=document.createElement('div');e.className='log live';d.appendChild(e);return e})();lg.textContent+=String.fromCharCode(10)+'· '+l;chat.scrollTop=chat.scrollHeight;});});},700);",
     "var LV=0,LT=setInterval(function(){J('/livesteps?last='+LV).then(function(g){(g.lines||[]).forEach(function(l){LV++;var lg=d.querySelector('.live')||(function(){var e=document.createElement('div');e.className='log live';d.appendChild(e);return e})();lg.textContent+=String.fromCharCode(10)+'· '+l;chat.scrollTop=chat.scrollHeight;});});},700);\nvar THI=0,THB=null,TT=setInterval(function(){J('/livethink?last='+THI).then(function(g){(g.toks||[]).forEach(function(t){THI++;if(!THB){THB=document.createElement('div');THB.className='thinkbody';d.appendChild(THB);}THB.textContent+=t;chat.scrollTop=chat.scrollHeight;});});},700);"),
    ("PAGE clear TT on done",
     "d._query=q;clearInterval(LT);clearInterval(ST2);",
     "d._query=q;clearInterval(LT);clearInterval(ST2);clearInterval(TT);"),
    ("PAGE clear TT on catch",
     ".catch(function(e){clearInterval(LT);clearInterval(ST2);",
     ".catch(function(e){clearInterval(LT);clearInterval(ST2);clearInterval(TT);"),
    ("thinkbody open by default",
     '<div class="thinkbody" style="display:none">',
     '<div class="thinkbody" style="display:block">'),
    ("fetch timeout 900s",
     "j(new Error('таймаут 300с: '+url))},300000)",
     "j(new Error('таймаут 900с: '+url))},900000)"),
]
for name, old, new in ITEMS:
    if new in a:
        SKIPS.append(name); print("[SKIP] %s: уже есть" % name)
    elif old in a:
        a = a.replace(old, new, 1); print("[OK] %s" % name)
    else:
        FAILS.append(name); print("[FAIL] якорь не найден: %s" % name)

if not FAILS:
    if py_ok(a, "agent.py"):
        (AG / "agent.py").write_text(a, encoding="utf-8")
        print("[OK] agent.py записан")
    else:
        FAILS.append("agent compile"); print("[FAIL] agent.py не компилируется, НЕ записан")
else:
    print("[WARN] agent.py НЕ записан из-за FAIL")

# --- settings.py: диапазон num_ctx ---
s = (AG / "settings.py").read_text(encoding="utf-8")
pat = re.compile(r'("num_ctx"\s*:\s*\(\s*)1024(\s*,\s*)65536(\s*,\s*)1024(\s*\))')
if "131072" in s and "num_ctx" in s:
    SKIPS.append("num_ctx range"); print("[SKIP] settings: диапазон уже расширен")
elif pat.search(s):
    s2 = pat.sub(r"\g<1>1024\g<2>131072\g<3>1024\g<4>", s, count=1)
    if py_ok(s2, "settings.py"):
        (AG / "settings.py").write_text(s2, encoding="utf-8")
        print("[OK] settings: num_ctx диапазон до 131072")
    else:
        FAILS.append("settings compile"); print("[FAIL] settings.py не компилируется, НЕ записана")
else:
    FAILS.append("num_ctx anchor"); print("[FAIL] settings: якорь диапазона num_ctx не найден")

print("\n=== CHECK ===")
ax = (AG / "agent.py").read_text(encoding="utf-8")
sx = (AG / "settings.py").read_text(encoding="utf-8")
print("LIVE_THINK:", "LIVE_THINK = {}" in ax)
print("/livethink:", '"/livethink"' in ax)
print("thinkbody block:", 'thinkbody" style="display:block"' in ax)
print("timeout 900:", "900000" in ax)
print("num_ctx 131072 в регистре:", "131072" in sx)
print()
if FAILS: print("НЕ ПРИМЕНЕНО: " + "; ".join(FAILS))
else: print("ГОТОВО: .\\AI_RESTART.bat + Ctrl+F5 в браузере")
if SKIPS: print("ПРОПУЩЕНО: " + "; ".join(SKIPS))