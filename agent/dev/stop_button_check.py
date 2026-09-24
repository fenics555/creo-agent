# -*- coding: utf-8 -*-
"""ПРОВЕРКА КНОПКИ «■ СТОП» (живая просьба хозяина 24.09.2026: «задал вопрос — передумал, а он всё пишет»).

Что проверяем на самом деле, а не «на глаз»:
  1) флаг отмены живёт ПО КЛИЕНТУ (чужой вопрос не глушится);
  2) поток-исполнитель узнаёт свой СТОП через _tokclient;
  3) СТОП РВЁТ поток к Ollama: чтение прекращается сразу, а не по концу генерации (считаем время);
  4) СТОП до начала хода = модель вообще не вызывается;
  5) обычный (не отменённый) путь не изменился: dict модели отдаётся как есть;
  6) провод в окно и в HTTP на месте (data-act="stop", /ask_cancel, AbortController).
"""
import json, os, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import loop  # noqa: E402

try:      # консоль Windows (cp1251/cp866) калечит эмодзи и роняет вывод (крах 24.09.2026)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

OK = [True]


def chk(name, cond, extra=""):
    print(("✅ " if cond else "❌ ") + name + (("  — " + str(extra)) if extra != "" else ""))
    if not cond:
        OK[0] = False


# --- 1. флаг по клиенту -------------------------------------------------------------------
loop.CANCEL.clear()
chk("до нажатия СТОП флага нет", loop._cancelled("t1") is False)
loop.cancel("t1")
chk("после СТОП флаг у клиента есть", loop._cancelled("t1") is True)
chk("другой клиент не задет", loop._cancelled("t2") is False)

# --- 2. поток узнаёт свой СТОП ------------------------------------------------------------
got = []


def _worker(cid):
    threading.current_thread()._tokclient = cid
    got.append((cid, loop._cancel_here()))


t = threading.Thread(target=_worker, args=("t1",)); t.start(); t.join()
t = threading.Thread(target=_worker, args=("t2",)); t.start(); t.join()
t = threading.Thread(target=_worker, args=("",)); t.start(); t.join()
chk("поток отменённого клиента видит СТОП", got[0][1] is True, got[0])
chk("поток другого клиента СТОП не видит", got[1][1] is False, got[1])
chk("поток без клиента СТОП не видит", got[2][1] is False, got[2])

# --- 3. СТОП рвёт поток к Ollama ----------------------------------------------------------
_real_get = loop.settings.get
loop.settings.get = lambda k, *a, **kw: 1 if k == "stream_tokens" else _real_get(k, *a, **kw)

LINES = 400          # «долгая» генерация: 400 строк по 10 мс = 4 с
SENT = [0]


class FakeResp:
    def __init__(self): pass
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def __iter__(self): return self._gen()

    def _gen(self):
        for i in range(LINES):
            time.sleep(0.01)
            SENT[0] += 1
            yield (json.dumps({"message": {"content": "токен%d " % i}, "done": False}) + "\n").encode("utf-8")


def _fake_urlopen(req, timeout=None):
    return FakeResp()


_real_urlopen = loop._ur.urlopen
loop._ur.urlopen = _fake_urlopen

out = []


def _ask_like():
    """Как настоящий запрос: свой поток, свой клиент, свой приёмник токенов."""
    threading.current_thread()._tokclient = "t1"
    threading.current_thread()._tokpush = lambda s: out.append(s)
    t0 = time.time()
    r = loop._stream_post("/api/chat", {"model": "fake", "messages": []})
    return r, time.time() - t0


loop.CANCEL.clear()
timer = threading.Timer(0.12, lambda: loop.cancel("t1"))   # «палец на кнопке» через 120 мс
timer.start()
r, dt = _ask_like()
timer.cancel()
loop._ur.urlopen = _real_urlopen
loop.settings.get = _real_get

chk("ответ помечен как отменённый", r.get("_cancelled") is True, r.get("_cancelled"))
chk("чтение оборвалось сразу (не ждали 400 строк)", dt < 1.0, "%.2f с из ~4.0 с" % dt)
chk("прочитано меньше, чем сгенерировано", SENT[0] < LINES, "%d из %d строк" % (SENT[0], LINES))
chk("частичный текст не потерян", "токен0" in (r["message"]["content"] or ""), (r["message"]["content"] or "")[:40])

# --- 4. СТОП до начала хода: модель не вызывается ------------------------------------------
CALLS = []
_real_post = loop.core.post
loop.core.post = lambda *a, **kw: (CALLS.append(a) or {"message": {"content": "[ANSWER]нет"}})
loop.cancel("t3")
rr = loop.run_loop([{"role": "user", "content": "тест"}], "t3")
loop.core.post = _real_post
loop.CANCEL.clear()
chk("ход не начался — модель не вызвана", CALLS == [], CALLS)
chk("ответ = «остановлено»", "остановлено" in rr.get("answer", ""), rr.get("answer", "")[:60])
chk("пометка отмены в результате", rr.get("cancelled") is True)

# --- 5. обычный путь не изменился ----------------------------------------------------------
loop.settings.get = lambda k, *a, **kw: 0 if k == "stream_tokens" else _real_get(k, *a, **kw)
loop._orig_core_post = lambda *a, **kw: {"message": {"content": "[ANSWER]живой ответ"}, "eval_count": 7}
threading.current_thread()._tokclient = "t9"
loop.CANCEL.clear()
r2 = loop._stream_post("/api/chat", {"model": "fake", "messages": []})
loop.settings.get = _real_get
chk("без стрима ответ проходит как раньше", r2.get("message", {}).get("content") == "[ANSWER]живой ответ", r2.get("message"))
chk("без стрима пометки отмены нет", "_cancelled" not in r2)

# --- 6. провод в окно и в HTTP -------------------------------------------------------------
app = open(os.path.join(ROOT, "ui", "app.js"), encoding="utf-8", errors="ignore").read()
hh = open(os.path.join(ROOT, "http_handlers.py"), encoding="utf-8", errors="ignore").read()
chk("в окне есть кнопка ■ СТОП", 'data-act="stop"' in app)
chk("в окне есть обработчик кнопки", "a=='stop'" in app)
chk("в окне есть обрыв запроса (AbortController)", "AbortController" in app and "signal:" in app)
chk("в окне есть Esc", "Escape" in app and "stopAsk()" in app)
chk("в окне зовётся /ask_cancel", "/ask_cancel" in app)
chk("в HTTP есть маршрут /ask_cancel", '"/ask_cancel"' in hh or "'/ask_cancel'" in hh)
chk("в HTTP импортирован отменяльщик", "cancel as ask_cancel" in hh)

# --- 7. полный путь ask(): отмена не портит историю -----------------------------------------
def _hist_n(cl):
    c = loop.core.db()
    n = c.execute("SELECT COUNT(*) FROM history WHERE client=?", (cl,)).fetchone()[0]
    c.close()
    return n


_real_build = loop.build_system
loop.build_system = lambda *a, **kw: "СИСТЕМА(тест кнопки СТОП)"
loop.core.post = lambda *a, **kw: {"message": {"content": "частичный ответ", "thinking": ""}, "_cancelled": True}
before = _hist_n("t4")
r3 = loop.ask("тест остановки генерации", "t4")
after = _hist_n("t4")
loop.core.post = _real_post
loop.build_system = _real_build
loop.CANCEL.clear()
chk("ask() отдал «остановлено»", "остановлено" in r3.get("answer", ""), r3.get("answer", "")[:60])
chk("ask() пометил отмену", r3.get("cancelled") is True)
chk("в историю НЕ записано", before == after, "было %d, стало %d" % (before, after))
chk("человеку сказано, что не записано", any("не записано" in s for s in r3.get("log", [])), r3.get("log", []))

# --- 8. живой HTTP: маршрут /ask_cancel реально принимает команду ---------------------------
import http.server, urllib.request, urllib.error  # noqa: E402
import http_handlers, users  # noqa: E402

srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), http_handlers.Hd)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
# токен кладём ТОЛЬКО в память — файл пользователей хозяина не трогаем
users.TOKENS["__stop_test__"] = {"login": "t_live", "ts": time.time()}
loop.CANCEL.clear()


def _post(path, tok=None, body=None):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path),
                                 data=json.dumps(body or {}).encode(),
                                 headers={"Content-Type": "application/json", "X-Token": tok or ""})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8") or "{}")


st_ok, js_ok = _post("/ask_cancel", "__stop_test__")
chk("HTTP /ask_cancel отвечает 200", st_ok == 200, st_ok)
chk("HTTP отвечает «стоп принят»", js_ok.get("msg") == "стоп принят", js_ok)
chk("HTTP поднял флаг у своего клиента", loop._cancelled("t_live") is True)
st_no, js_no = _post("/ask_cancel")
chk("без входа маршрут закрыт (401)", st_no == 401, (st_no, js_no))
st_bad, js_bad = _post("/ask_cancel_bogus", "__stop_test__")
chk("выдуманный маршрут НЕ отвечает «стоп принят»", js_bad.get("msg") != "стоп принят", (st_bad, js_bad))
srv.shutdown()
users.TOKENS.pop("__stop_test__", None)
loop.CANCEL.clear()

# --- уборка: проверка не должна оставлять следов в журнале дома -----------------------------
try:
    _p = os.path.join(ROOT, "data", "chains.jsonl")
    if os.path.exists(_p):
        _ls = open(_p, encoding="utf-8").read().splitlines()
        _k = [l for l in _ls if "тест остановки генерации" not in l]
        if len(_k) != len(_ls):
            open(_p, "w", encoding="utf-8").write("\n".join(_k) + ("\n" if _k else ""))
            print("🧹 журнал цепочек очищен от строк теста: %d" % (len(_ls) - len(_k)))
except Exception as _e:
    print("⚠ журнал цепочек не очищен: %s" % _e)

print("")
print("ИТОГ: " + ("ВСЁ ЗЕЛЁНОЕ — кнопка СТОП работает" if OK[0] else "ЕСТЬ ОШИБКИ — см. ❌ выше"))
sys.exit(0 if OK[0] else 1)
