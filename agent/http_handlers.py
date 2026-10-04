# -*- coding: utf-8 -*-
"""АГЕНТ v15 — http_handlers.py: HTTP-обработчики витрины (do_GET/do_POST)."""
import json, os, socket, threading, datetime, re, subprocess, sys, time
from urllib.parse import urlparse, parse_qs
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import core
from core import log, trace
import settings
import pdf_tools
import prog_tools
import users
import chat_tools
import panel
import tools_registry as TR
import vision_tools as VI
from loop import (LIVE_TOK, LIVE_THINK, LIVE, PENDING, HOSTNAME, UI_FILE,
                  _UI_CACHE, STUB_PAGE, _SYS_CACHE, ask, do_approve, cancel as ask_cancel)
from agent_sched import _wd_port

def _serve_ui(handler):
    try:
        mt = int(os.path.getmtime(UI_FILE))
        if _UI_CACHE[0] != mt:
            _UI_CACHE[0] = mt
            _UI_CACHE[1] = open(UI_FILE, "rb").read()
        b = _UI_CACHE[1]
    except Exception:
        b = STUB_PAGE.encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    # ЖИВОЙ ДЕФЕКТ 03.10.2026 (слово владельца «открылся старый агент»): было `no-cache`
    # БЕЗ ETag/Last-Modified. `no-cache` требует перепроверки, но перепроверять нечем —
    # браузер при возврате на вкладку отдавал старый index.html, и владелец видел
    # витрину вчерашнего дня. Витрина агента обязана быть `no-store`: она меняется
    # при каждой правке, кэшировать её нечего.
    handler.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
    handler.send_header("Pragma", "no-cache")
    handler.send_header("Expires", "0")
    handler.send_header("Content-Length", str(len(b)))
    handler.end_headers()
    handler.wfile.write(b)


# Отдача статики витрины (варианты окна, картинки). Только из папки ui\, без «..» и левых расширений.
STATIC_EXT = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
              ".css": "text/css; charset=utf-8", ".png": "image/png", ".svg": "image/svg+xml",
              ".json": "application/json; charset=utf-8", ".md": "text/plain; charset=utf-8"}


def _serve_file(handler, rel):
    rel = (rel or "").replace("\\", "/").lstrip("/")
    ext = os.path.splitext(rel)[1].lower()
    if ".." in rel or ext not in STATIC_EXT:
        return handler._j({"error": "плохой путь: %s" % rel}, 400)
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", rel.replace("/", os.sep))
    if not os.path.isfile(p):
        return handler._j({"error": "нет файла ui\\%s" % rel}, 404)
    with open(p, "rb") as f:
        b = f.read()
    handler.send_response(200)
    handler.send_header("Content-Type", STATIC_EXT[ext])
    handler.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
    handler.send_header("Pragma", "no-cache")
    handler.send_header("Expires", "0")
    handler.send_header("Content-Length", str(len(b)))
    handler.end_headers()
    handler.wfile.write(b)


class Hd(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _j(self, d, code=200):
        b = json.dumps(d, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) or b"{}"
        try: return json.loads(raw)
        except Exception:
            s = raw.decode("utf-8-sig", "ignore")
            if s.lstrip().startswith("{"):
                try: return json.loads(s.replace('\\"', '"'))
                except Exception: return {}
            return {}

    def _client(self, b):
        u = users.token_info(b.get("token") or self.headers.get("X-Token") or "")
        return u["login"] if u else None

    def do_GET(self):
        p = urlparse(self.path).path
        print(f"DEBUG: p={p}")
        if p == "/status":
            token = self.headers.get("X-Token") or ""
            cl2 = users.token_info(token)
            prof = users.get_profile(cl2["login"]) if cl2 else None
            tail = ""
            if cl2:
                try:
                    jf = core.REPO / "Трейлы" / "TRAIL_JOURNAL.md"
                    if jf.exists():
                        tail = "\n".join(jf.read_text(encoding="utf-8", errors="ignore").splitlines()[-8:])
                except Exception:
                    tail = ""
            def _alive(p_):
                try:
                    s_ = socket.create_connection(("127.0.0.1", p_), timeout=1); s_.close(); return True
                except Exception: return False
            # Окно активной модели (данные, а не догадки) — человек вписывает его цифрой в «Окно контекста».
            _mctx = None
            _sctx = None
            try:
                import settings_tools as _st50
                _mctx = _st50._model_info(settings.model_for("chat")).get("ctx")
                _sctx = _st50.loaded_ctx()
            except Exception:
                _mctx = None
            self._j({"host": HOSTNAME, "model": settings.get("llm_model"), "blocks": len(TR.BLOCKS),
                     "tools": len(TR.TOOLS), "user": prof, "model_ctx": _mctx,
                     "ctx_requested": int(settings.get("num_ctx") or 0), "ctx_session": _sctx,
                     "is_manager": users.can_manage_users(prof["login"]) if prof else False,
                     "trails": tail, "mode": settings.get_for(cl2["login"], "chat_mode", 1) if cl2 else 1,
                     "ui_layout": settings.get_for(cl2["login"], "ui_layout", "v2") if cl2 else "v2",
                     "up_ollama": _alive(11434), "up_creoson": _alive(8080), "up_agent": True})
            return
        elif p == "/health":
            if not users.token_info(self.headers.get("X-Token") or ""): return self._j({"error": "no token"})
            self._j({"ollama": _wd_port(11434), "creoson": _wd_port(8080), "agent": True})
            return
        elif p == "/api/programs":
            if not users.token_info(self.headers.get("X-Token") or ""):
                return self._j({"error": "нужен вход"})
            self._j(prog_tools.prog_list(as_json=True))
            return
        elif p == "/api/tools":
            # СПИСОК ИНСТРУМЕНТОВ (слово владельца 03.10.2026: «где вкладка, где инструменты
            # 100+?»). Раньше витрина знала ТОЛЬКО счётчики (`/status`: 180 инструментов),
            # а сам список был недоступен из интерфейса — вкладку негде было показать.
            import tools_registry as _TR
            try:
                # Живой API реестра: `all()` тут нет, есть `iter_tools()` — отдаёт
                # (kind, group, tool). Считать из выдуманного метода нельзя.
                _lst = [{"name": t.get("name"), "desc": t.get("desc") or "",
                         "group": g or "", "kind": k or "",
                         "approval": bool(t.get("approval")),
                         "needs_creo": bool(t.get("needs_creo"))}
                        for k, g, t in _TR.iter_tools()]
            except Exception as _tr_e:
                return self._j({"error": "реестр не прочитан: %s" % _tr_e, "tools": []})
            _out = sorted(_lst, key=lambda x: ((x["group"] or ""), (x["name"] or "")))
            _gs = {}
            for _x in _out:
                _gs.setdefault(_x["group"], 0)
                _gs[_x["group"]] += 1
            return self._j({"tools": _out, "count": len(_out),
                            "groups": [{"id": g, "title": g, "icon": "•", "n": n}
                                       for g, n in sorted(_gs.items(), key=lambda kv: -kv[1])],
                            "error": None})
        elif p == "/api/bases":
            if not users.token_info(self.headers.get("X-Token") or ""):
                return self._j({"error": "нужен вход"})
            self._j({"bases": prog_tools.bases_list(as_json=True)})
            return
        elif p == "/api/jobs":
            if not users.token_info(self.headers.get("X-Token") or ""):
                return self._j({"error": "нужен вход"})
            self._j({"lines": core.jobs_tail(60)})
            return
        elif p == "/pdfpages":
            if not users.token_info(self.headers.get("X-Token") or ""): return self._j({"error": "no token"})
            qs = parse_qs(urlparse(self.path).query)
            name = qs.get("name", [""])[0]
            if not name: return self._j({"error": "no name"})
            self._j(pdf_tools.pdf_pages(name))
            return
        # /pdfimg обслуживается общим блоком /pdfthumb|/pdfimg ниже (PNG-байты
        # для <img src> + токен из заголовка или query) — ранний JSON-вариант
        # снят 66e/N10: витрина ждёт image/png, а не словарь pdf_img.
        elif p == "/pdfstatus":
            if not users.token_info(self.headers.get("X-Token") or ""): return self._j({"error": "no token"})
            qs = parse_qs(urlparse(self.path).query)
            name = qs.get("name", [""])[0]
            if not name: return self._j({"error": "no name"})
            self._j(pdf_tools.pdf_status(name))
            return
        elif p == "/children":
            if not users.token_info(self.headers.get("X-Token") or ""): return self._j({"error": "no token"})
            qs = parse_qs(urlparse(self.path).query)
            name = qs.get("name", [""])[0]
            if not name: return self._j({"error": "no name"})
            out = []
            try:
                c = core.db()
                for sql in ("SELECT child FROM usage WHERE parent LIKE ?",
                            "SELECT child FROM bom WHERE parent LIKE ?",
                            "SELECT child FROM links WHERE parent LIKE ?"):
                    try:
                        rows = c.execute(sql, ("%" + name + "%",)).fetchall()
                        out = [r[0] for r in rows]
                    except Exception:
                        continue
                    if out: break
                c.close()
            except Exception as e:
                self._j({"error": str(e)}); return
            self._j({"name": name, "children": out[:200]})
            return
        elif p == "/graph/data":
            if not users.token_info(self.headers.get("X-Token") or ""): return self._j({"error": "no token"})
            qs = parse_qs(urlparse(self.path).query)
            name = qs.get("name", [""])[0]
            if not name: return self._j({"error": "no name"})
            import graph_tools
            self._j(graph_tools.build_graph(name))
            return
        elif p == "/graph":
            if not users.token_info(self.headers.get("X-Token") or ""):
                self.send_response(401); self.end_headers(); return
            b = open(os.path.join(os.path.dirname(__file__), "ui", "graph.html"), "rb").read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
            return
        elif p == "/map/data":
            if not users.token_info(self.headers.get("X-Token") or ""): return self._j({"error": "no token"})
            qs = parse_qs(urlparse(self.path).query)
            top = int(qs.get("top", ["100"])[0])
            import map_tools
            self._j(map_tools.build_map(top))
            return
        elif p == "/map":
            if not users.token_info(self.headers.get("X-Token") or ""):
                self.send_response(401); self.end_headers(); return
            b = open(os.path.join(os.path.dirname(__file__), "ui", "map.html"), "rb").read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
            return
        elif p == "/pdfregistry":
            if not users.token_info(self.headers.get("X-Token") or ""): return self._j({"error": "no token"})
            try:
                c = core.db()
                rows = c.execute("SELECT path, mtime FROM files").fetchall()
                c.close()
            except Exception as e:
                self._j({"error": str(e)}); return
            bydir = {}
            for path, mt in rows:
                bydir.setdefault(os.path.dirname(path), {})[os.path.basename(path).lower()] = (path, mt)
            pairs = []
            # ЖИВАЯ НАХОДКА 02.10.2026 (аудит agent\data): переменная seen_names тут же
            # использовалась (строки ниже), но НИКОГДА не создавалась — NameError рвал соединение,
            # и витрина PDF молча показывала пустую страницу. Имена уже показанных моделей
            # не должны повторяться в разных папках.
            seen_names = set()
            for d, fs in bydir.items():
                du = d.upper()
                if "\\CREO12\\" in du or "\\DATA\\" in du:
                    continue
                for nm, (path, mt) in fs.items():
                    if nm in seen_names: continue
                    verdict, entry = None, {}
                    m = re.search(r"(.*?)\.(drw|asm|prt)(\.\\d+)?$", nm, re.I)
                    if m:
                        base_nm, ext, suffix = m.groups()
                        suffix = suffix or ""
                        if ext.lower() == "drw":
                            stem = base_nm
                            pdf = fs.get(stem + ".pdf")
                            verdict = "нет pdf" if not pdf else ("актуален" if pdf[1] >= mt else "УСТАРЕЛ")
                            entry = {"name": nm, "dir": d, "drw": path, "pdf": pdf[0] if pdf else "",
                                     "drw_mtime": mt, "pdf_mtime": pdf[1] if pdf else 0, "verdict": verdict}
                        else:
                            drw = fs.get(base_nm + ".drw" + suffix)
                            pdf = fs.get(base_nm + ".pdf")
                            if drw:
                                drw_p, drw_mt = drw
                                if pdf:
                                    pdf_p, pdf_mt = pdf
                                    v = "актуален" if pdf_mt >= drw_mt else "устарел"
                                    verdict = f"pdf через чертёж {base_nm}.drw{suffix}: {v}"
                                else:
                                    verdict = f"чертёж {base_nm}.drw{suffix}: нет pdf"
                                    pdf_p, pdf_mt = "", 0
                                entry = {"name": nm, "dir": d, "drw": drw_p, "pdf": pdf_p,
                                         "drw_mtime": drw_mt, "pdf_mtime": pdf_mt, "verdict": verdict}
                            else:
                                verdict = "чертежа нет"
                                entry = {"name": nm, "dir": d, "drw": "", "pdf": "",
                                         "drw_mtime": 0, "pdf_mtime": 0, "verdict": verdict}
                    if verdict:
                        pairs.append(entry)
                        seen_names.add(nm)
                        if len(pairs) >= 500: break
                if len(pairs) >= 500: break
            pairs.sort(key=lambda r: (r["verdict"] != "УСТАРЕЛ", r["name"]))
            self._j({"pairs": pairs, "total": len(pairs)})
            return
        elif p in ("/pdfthumb", "/pdfimg"):
            qs = parse_qs(urlparse(self.path).query)
            _tk = users.token_info(self.headers.get("X-Token") or qs.get("token", [""])[0])
            if not _tk:
                if p == "/pdfimg":
                    self.send_response(401); self.end_headers(); return
                self._j({"error": "token required"})
                return
            nm = qs.get("name", [None])[0]
            pg = qs.get("page", ["1"])[0]
            res = pdf_tools.pdf_img(nm, pg)
            if "error" in res:
                self._j({"error": "миниатюры нет"})
                return
            img_path = res["image_path"]
            try:
                with open(img_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self._j({"error": f"failed to serve image: {e}"})
            return

        elif p == "/panel":
            if not users.token_info(self.headers.get("X-Token") or ""):
                self.send_response(401); self.end_headers(); return
            d = panel.build()
            _ui = users.token_info(self.headers.get("X-Token") or "")
            if not (_ui and users.is_admin(_ui["login"])):
                d["groups"] = [g for g in d.get("groups", []) if "НАСТРОЙКИ" not in str(g.get("title", "")).upper()]
                d.pop("settings", None)
            self._j(d)
            return
        elif p == "/log":
            _tk = users.token_info(self.headers.get("X-Token") or "")
            if _tk and not users.is_admin(_tk["login"]):
                c = core.db()
                rows = c.execute("SELECT q,a,ts FROM history WHERE client=? ORDER BY id DESC LIMIT 40", (_tk["login"],)).fetchall()
                c.close()
                self._j({"log": "\n".join("%s · %s → %s" % (ts[:16], q, a[:80]) for q, a, ts in reversed(rows)) or "история пуста"})
                return
            else:
                try:
                    txt = core.LOGF.read_text(encoding="utf-8", errors="ignore").splitlines()
                    self._j({"log": "\n".join(txt[-80:])})
                    return
                except Exception:
                    self._j({"log": "лога нет"})
                    return
        elif p == "/settings":
            self._j({"items": settings.list_ui()})
            return
        elif p == "/livetoks":
            _cl6 = users.token_info(self.headers.get("X-Token") or "")
            qs = parse_qs(urlparse(self.path).query)
            last = int((qs.get("last") or ["0"])[0])
            toks = LIVE_TOK.get(_cl6["login"] if _cl6 else "", [])
            self._j({"toks": toks[last:], "last": len(toks)})
            return
        elif p == "/livethink":
            _cl7 = users.token_info(self.headers.get("X-Token") or "")
            qs7 = parse_qs(urlparse(self.path).query)
            last7 = int((qs7.get("last") or ["0"])[0])
            ths = LIVE_THINK.get(_cl7["login"] if _cl7 else "", [])
            self._j({"toks": ths[last7:], "last": len(ths)})
            return
        elif p == "/livesteps":
            _cl4 = users.token_info(self.headers.get("X-Token") or "")
            qs = parse_qs(urlparse(self.path).query)
            last = int((qs.get("last") or ["0"])[0])
            lines = LIVE.get(_cl4["login"] if _cl4 else "", [])
            self._j({"lines": lines[last:], "last": len(lines)})
            return
        elif p == "/fleet/info":
            if not users.token_info(self.headers.get("X-Token") or ""):
                self._j({"error": "нужен вход"}, code=401)
                return
            tail = ""
            try:
                jf = core.REPO / "Трейлы" / "TRAIL_JOURNAL.md"
                if jf.exists():
                    tail = "\n".join(jf.read_text(encoding="utf-8", errors="ignore").splitlines()[-10:])
            except Exception: pass
            self._j({"tail": tail})
            return
        elif p.startswith("/ui/"):
            _serve_file(self, p[4:])
            return
        else:
            _serve_ui(self)

    def do_POST(self):
        p = urlparse(self.path).path
        b = self._body()
        if p == "/login":
            r = users.check_login(b.get("login"), b.get("pw") or b.get("password"))
            self._j(r or {"ok": False}); return
        if p == "/register":
            okf = users.add_user(b.get("login"), b.get("pw") or b.get("password"))
            self._j({"msg": "пользователь создан" if okf else "логин занят или пустой"}); return
        cl = self._client(b)
        if not cl:
            self._j({"error": "нужен вход"}, 401); return
        if p == "/ask_cancel":
            # ■ СТОП: человек передумал — рвём генерацию этой модели (живая просьба хозяина 24.09.2026)
            ask_cancel(cl)
            self._j({"ok": True, "msg": "стоп принят"}); return
        if p == "/ask":
            self._j(ask(b.get("q") or "", cl, b.get("image"), mode=b.get("mode")))
        elif p == "/ask_stream":
            import queue as _q
            qq = _q.Queue(); holder = {}

            def _cb(line): qq.put(line)

            def _run():
                try: holder["r"] = ask(b.get("q") or "", cl, b.get("image"), on_step=_cb, mode=b.get("mode"))
                except Exception as e: holder["r"] = {"answer": "ошибка: %s" % e, "log": []}
                finally: qq.put(None)
            threading.Thread(target=_run, daemon=True).start()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            # 04.10.2026 (аудит настроек): настройка `stream_ui` («токены в чат по мере генерации»)
            # была объявлена, но НИГДЕ не читалась — веб шлёт только шаги (on_step), а токены,
            # которые агент уже копит в LIVE_TOK, до витрины не доходили. Теперь при включённой
            # настройке поток токенов уходит в том же SSE-потоке.
            _toks_on = bool(settings.get("stream_ui"))
            _seen_tok = [0]
            # Логин клиента берём ЗДЕСЬ: переменная _cl6 живёт только в ветке /livetoks,
            # и обращение к ней отсюда было бы NameError (найдено компиляцией правки).
            _cl8 = users.token_info(self.headers.get("X-Token") or "")
            _deadline = time.time() + 900
            while True:
                # Токены забираем между шагами неблокирующе: очередь шагов может молчать минутами,
                # а ждать её get() без таймаута — вечно (старый код на этом и висел).
                if _toks_on:
                    try:
                        _tk = LIVE_TOK.get(_cl8["login"] if _cl8 else "", [])
                        if len(_tk) > _seen_tok[0]:
                            self.wfile.write(("data: %s\n\n" % json.dumps({"tok": _tk[_seen_tok[0]:]}, ensure_ascii=False)).encode())
                            self.wfile.flush()
                            _seen_tok[0] = len(_tk)
                    except Exception:
                        pass
                try:
                    item = qq.get(timeout=0.3)
                except Exception:
                    if time.time() > _deadline:
                        self.wfile.write(("data: %s\n\n" % json.dumps({"error": "превышено время ожидания"}, ensure_ascii=False)).encode())
                        self.wfile.flush()
                        return
                    continue
                if item is None: break
                self.wfile.write(("data: %s\n\n" % json.dumps({"step": item}, ensure_ascii=False)).encode()); self.wfile.flush()
            if _toks_on:
                try:
                    _tk = LIVE_TOK.get(_cl8["login"] if _cl8 else "", [])
                    if len(_tk) > _seen_tok[0]:
                        self.wfile.write(("data: %s\n\n" % json.dumps({"tok": _tk[_seen_tok[0]:]}, ensure_ascii=False)).encode())
                        self.wfile.flush()
                except Exception:
                    pass
            self.wfile.write(("data: %s\n\n" % json.dumps({"done": holder.get("r", {})}, ensure_ascii=False)).encode()); self.wfile.flush()
            return
        elif p == "/approve":
            self._j(do_approve(b.get("pid"), b.get("ok")))
        elif p == "/wiz_preview":
            import copy_tools as _cp37
            self._j(_cp37.preview(old=b.get("old") or "", new=b.get("new") or "", template=b.get("template") or "",
                                  family=b.get("family", 1), drawings=b.get("drawings", 0)))
        elif p == "/wiz_rename_preview":
            import rename_tools as _rn37
            self._j(_rn37.build_plan(old=b.get("old") or "", new=b.get("new") or "",
                                     drawings=b.get("drawings", 1)))
        elif p == "/setmodel":
            # ЛИЧНЫЙ ВЫБОР МОДЕЛИ — ТОЛЬКО АДМИН (требование дома 24.09.2026: одна модель на дом,
            # агент и Cline не должны гонять веса в память; случайная смена модель ломает это всем).
            if not users.is_admin(cl):
                self._j({"error": "смена модели — только админ"}, 403)
                return
            import panel as _pn
            ok_names = _pn.models()
            want = b.get("model") or ""
            if want not in ok_names:
                self._j({"ok": False, "error": "нет такой модели", "models": ok_names}, 400)
                return
            settings.set_val("llm_model", want)
            self._j({"ok": True})
        elif p == "/setauto":
            if not users.is_admin(cl):
                self._j({"error": "настройки — только админ"}, 403)
                return
            settings.set_val("auto_mode", 1 if b.get("on") else 0); self._j({"ok": True})
        elif p == "/feedback":
            try:
                c = core.db()
                c.execute("CREATE TABLE IF NOT EXISTS feedback(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, client TEXT, query TEXT, think TEXT, tool TEXT, result TEXT, ok INTEGER, comment TEXT)")
                c.execute("INSERT INTO feedback(ts,client,query,think,tool,result,ok,comment) VALUES(?,?,?,?,?,?,?,?)",
                          (datetime.datetime.now().isoformat(), cl, (b.get("query") or "")[:2000], (b.get("think") or "")[:2000],
                           (b.get("tool") or "")[:120], (b.get("result") or "")[:2000], 1 if b.get("ok") else 0, (b.get("comment") or "")[:500]))
                c.commit(); c.close()
            except Exception as e:
                self._j({"ok": False, "msg": "оценка не сохранена: %s" % e}, 500); return
            self._j({"ok": True, "msg": "оценка сохранена"})
        elif p == "/setcfg":
            if (b.get("key") or "") in settings.PERSONAL_KEYS:
                settings.set_for(cl, b.get("key"), b.get("value")); self._j({"ok": True}); return
            if not users.is_admin(cl):
                self._j({"error": "настройки — только админ"}, 403); return
            settings.set_val(b.get("key"), b.get("value")); _SYS_CACHE.clear(); self._j({"ok": True})
        elif p == "/snap":
            self._j({"msg": "скриншот принимается через Ctrl+V в поле ввода"})
        elif p == "/prog_state":
            self._j({"text": prog_tools.prog_state(b.get("prog_id") or "", b.get("tail") or 20)})
        elif p == "/prog_run":
            self._j({"text": prog_tools.prog_run(b.get("prog_id") or "", b.get("args") or "")})
        elif p == "/rescan" or p == "/scan":
            # Запуск через prog_tools: движок идёт в фон, а дом получает строки в ОБЩИЙ ЖУРНАЛ РАБОТ
            # («запущено в фоне» … «завершено …»). Раньше был прямой Popen и в журнале ничего не оставалось.
            self._j({"msg": prog_tools.prog_run(prog_id="harvest"),
                     "report": r"D:\AI\log\harvest\last_harvest.json",
                     "z_status": "Z запрещён словом, пропущен"})
        elif p == "/profile":
            __prof = users.get_profile(cl)
            if __prof:
                __prof = dict(__prof)
                __prof["can_manage"] = users.can_manage_users(cl)
            self._j(__prof or {"error": "нет профиля"})
        elif p == "/wiz_purge_preview":
            import purge_versions
            from pathlib import Path
            root = b.get("root")
            # ЖИВАЯ НАХОДКА 03.10.2026 (аудит data\, Д3): без ключа root шёл Path(None) ->
            # TypeError -> соединение рвалось ("Remote end closed connection"), и в окне это
            # выглядело как «агент завис». Теперь — внятный ответ с кодом 400.
            if not root:
                return self._j({"error": "укажите корень (root) — папку, где чистильщик ищет версии"}, code=400)
            keep = int(b.get("keep") or 1)
            creo_mode = b.get("creo_mode") == "true"
            try:
                res = purge_versions.preview(Path(root), keep, creo_mode)
            except Exception as e:
                return self._j({"error": "не разобрал корень %s: %s" % (root, e)}, code=400)
            rows = []
            total = 0
            for g in res["groups"]:
                old = g["base"]
                new = g["target"]
                versions = len(g["members"])
                rows.append({"old": old, "new": new, "versions": versions})
                total += 1
            for s in res["singles"]:
                rows.append({"old": s, "new": s, "versions": 1})
                total += 1
            self._j({"rows": rows, "total": total, "error": None})
        elif p == "/wiz_purge_execute":
            import purge_versions
            from pathlib import Path
            root = Path(b.get("root"))
            keep = int(b.get("keep") or 1)
            creo_mode = b.get("creo_mode") == "true"
            backup_dir = root / "_purge_backup" / datetime.datetime.now().strftime("%Y%m%d")
            res = purge_versions.execute(root, keep, creo_mode, backup_dir)
            self._j(res)
        elif p == "/wiz_orphan_preview":
            # Третья рука orphan_scan (манифест п.19): визард в витрине под щитом
            # согласования. Только чтение — ничего не меняет.
            # ВНИМАНИЕ: в ветке /wiz_plmtree ниже есть `import os as _os` — из-за него
            # `_os` становится ЛОКАЛЬНОЙ переменной всей do_POST и падает
            # UnboundLocalError. Здесь имя другое (живой отказ 02.10.2026).
            import os as _oso
            import sys as _sys2
            _ot = _oso.path.join(_oso.path.dirname(_oso.path.abspath(__file__)), "orphan_scan")
            if _ot not in _sys2.path:
                _sys2.path.insert(0, _ot)
            import orphan_scan as _os37
            root = (b.get("root") or "").strip()
            if not root:
                return self._j({"error": "укажите папку"})
            _sc = _os37.OrphanScanner()
            _sc.scan(roots=[root])
            rows = [{"kind": "СИРОТА", "path": p} for p in _sc.orphans[:200]]
            rows += [{"kind": "модель в другом месте", "path": p}
                     for p in _sc.model_elsewhere_list[:200]]
            return self._j({"rows": rows, "stats": _sc.stats,
                            "roots": _sc.roots, "error": None})
        elif p == "/wiz_config_audit":
            # Третья рука config_audit (манифест п.19): визард витрины под щитом
            # согласования. Только чтение — конфиг не меняется.
            # ВСЁ тело в try/except: иначе исключение рвёт соединение, клиент видит
            # RemoteDisconnected и никакой причины (живая проверка 02.10.2026).
            try:
                import sys as _sys3
                import os as _cfa_os
                # ВНИМАНИЕ: в ветке /wiz_plmtree ниже есть `import os as _os`, из-за чего `_os`
                # становится ЛОКАЛЬНОЙ переменной всей do_POST; имена здесь свои.
                _ct = _cfa_os.path.join(_cfa_os.path.dirname(_cfa_os.path.abspath(__file__)),
                                        "config_audit")
                if _ct not in _sys3.path:
                    _sys3.path.insert(0, _ct)
                import config_audit as _ca37
                cfg = (b.get("config") or _ca37.CONFIG).strip()
                if not _cfa_os.path.isfile(cfg):
                    return self._j({"error": "нет файла config.pro: %s" % cfg})
                res = _ca37.audit(cfg)
                rep = None
                try:
                    rep = _ca37.write_report(res, cfg, 0.0, quiet=True)
                except Exception:
                    pass
                return self._j({
                    "config": cfg,
                    "total": res["total"],
                    "missing": res["missing"],
                    "problems": [{"line": pr["line"], "opt": pr["opt"],
                                  "value": pr["value"], "path": pr["path"]}
                                 for pr in res["problems"][:200]],
                    "vars": dict(_ca37.load_vars() or {}),
                    "report": rep,
                    "error": None})
            except Exception as _cfa_e:
                import traceback as _cfa_tb
                trace = traceback.format_exc()[-800:]
                try:
                    log("wiz_config_audit FAILED: %s" % trace)
                except Exception:
                    pass
                return self._j({"error": "%s: %s" % (type(_cfa_e).__name__, _cfa_e)})
        elif p == "/wiz_plmtree":
            import contextlib
            import io
            # 03.10.2026: было `sys.path.insert + import engine` — в доме четыре файла engine.py,
            # и обычный импорт мог отдать чужой модуль из sys.modules. Теперь единая точка входа:
            # обёртка plm_reader_tools грузит движок по явному пути (importlib).
            import plm_reader_tools as _PRT
            _eng = _PRT.engine()
            cmd = b.get("cmd") or "tree"
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                if cmd == "where":
                    _eng.do_where(b.get("model") or "")
                elif cmd == "rename-plan":
                    _eng.do_rename_plan(b.get("model") or "", b.get("new") or "")
                else:
                    _eng.do_tree(b.get("model") or "", int(b.get("depth") or 4))
            self._j({"text": buf.getvalue()})

        elif p == "/wiz_check_run":
            # Третья рука checks (манифест п.19, долг волны 11): экран «Проверки» в витрине.
            # ТОЛЬКО ЧТЕНИЕ — проверки ничего не меняют. Всё тело в try/except, иначе
            # исключение рвёт соединение и клиент видит RemoteDisconnected без причины
            # (живой отказ 02.10.2026 на /wiz_config_audit — тот же приём).
            # ВНИМАНИЕ: в ветке /wiz_plmtree выше есть `import os as _os` — из-за него `_os`
            # становится ЛОКАЛЬНОЙ переменной всей do_POST. Здесь имена свои.
            try:
                import checks as _chk37
                scope = (b.get("scope") or "").strip()
                only = (b.get("only") or "").strip()
                res = _chk37.checks_run(scope, only, as_json=True)
                report = None
                if b.get("report") == "true":
                    try:
                        report = _chk37.write_report(res)
                    except Exception as _wr_e:
                        report = "отчёт не записан: %s" % _wr_e
                return self._j({"result": res, "report": report, "error": None})
            except Exception as _chk_e:
                import traceback as _chk_tb
                trace = traceback.format_exc()[-800:]
                try:
                    log("wiz_check_run FAILED: %s" % trace)
                except Exception:
                    pass
                return self._j({"result": None, "report": None,
                                "error": "%s: %s" % (type(_chk_e).__name__, _chk_e)})
        elif p == "/ui_readme":
            # Слой 7 канона ОКНА (01_СТРОЕНИЕ_ОКНА.md): «кнопка README — обязательна:
            # читает README.md и печатает в лог построчно; при ошибке — честная строка».
            # Для витрины README — это её собственный документ.
            _p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md")
            try:
                _t = open(_p, encoding="utf-8").read()
            except Exception as _re_e:
                return self._j({"error": "README не прочитан: %s" % _re_e})
            return self._j({"text": _t, "path": _p, "error": None})
        elif p == "/wiz_rules":
            # ПРАВИЛА ДВУСТОРОННИЕ — по образцу B&W (конспект 17, §3 «Диалог правил»):
            # сверху ТЕКСТ (IF…THEN, его читает движок), снизу ФОРМА (её правит человек),
            # порядок правил важен → Up/Down, кнопки New/Delete/Update/Close.
            import rules_engine as _RE
            op = (b.get("op") or "get")
            try:
                if op == "get":
                    _doc, _err = _RE.load()
                    if not _doc:
                        return self._j({"error": "правила не прочитались: %s" % _err,
                                        "rules": [], "text": ""})
                    return self._j({"rules": _doc.get("rules") or [],
                                    "text": _RE.all_text(_doc),
                                    "file": str(_RE.RULES_FILE),
                                    "stats": _RE.stats(_doc), "error": None})
                # запись: принимаем ПОЛНЫЙ документ и пишем через движок (он же валидирует)
                _new = b.get("doc")
                if not isinstance(_new, dict):
                    return self._j({"error": "пришли doc — объект правил"})
                _e2 = _RE.validate(_new)
                if _e2:
                    return self._j({"error": "не сохранено — ошибки валидации: %s"
                                    % "; ".join(map(str, _e2))})
                _RE.save(_new)
                return self._j({"ok": True, "saved": str(_RE.RULES_FILE),
                                "stats": _RE.stats(_new), "error": None})
            except Exception as _rx_e:
                return self._j({"error": "%s: %s" % (type(_rx_e).__name__, _rx_e)})
        elif p == "/wiz_batch":
            # ПАКЕТНЫЙ РЕЖИМ — по образцу B&W (конспект 17, §7 «Batch Mode»):
            # таблица Name | Progress | Status | Fixed Errors + СВОДКА В ЗАГОЛОВКЕ окна.
            # Источник — живой журнал `/api/jobs` («РАБОТА <id>: запущено/завершено»),
            # а не выдуманные цифры: прогресс и «исправлено ошибок» берутся из текста строк.
            if not cl:
                return self._j({"error": "нужен вход"})
            import re as _re2
            try:
                # ЖИВОЙ источник — `core.jobs_tail()` (его же зовёт /api/jobs и инструмент
                # jobs_show). Метода `prog_tools.journal_lines()` в доме НЕТ.
                _lines = core.jobs_tail(400)
            except Exception as _jl_e:
                return self._j({"error": "журнал работ не прочитан: %s" % _jl_e, "rows": []})
            runs = {}
            for ln in str(_lines).splitlines():
                m = _re2.search(r"(\d\d-\d\d \d\d:\d\d:\d\d)\s+\D*РАБОТА\s+([A-Za-z0-9_]+):\s*(запущено|завершено)(.*)", ln)
                if not m:
                    continue
                ts, pid, kind, tail = m.groups()
                r = runs.setdefault(pid, {"name": pid, "started": None, "finished": None,
                                          "status": "неизвестно", "code": None, "secs": None,
                                          "fixed": None, "log": ""})
                if kind == "запущено":
                    r["started"] = ts
                    r["status"] = "Выполняется"
                else:
                    r["finished"] = ts
                    c = _re2.search(r"code=(-?\d+)", tail)
                    s = _re2.search(r"секунд=([\d.]+)", tail)
                    lg = _re2.search(r"лог=(\S+)", tail)
                    r["code"] = int(c.group(1)) if c else None
                    r["secs"] = float(s.group(1)) if s else None
                    r["log"] = lg.group(1) if lg else ""
                    r["status"] = "Готово" if r["code"] == 0 else ("Ошибка" if r["code"] else "Завершено")
            out = list(runs.values())[-60:]
            out.reverse()
            done = sum(1 for x in out if x["status"] == "Готово")
            bad = sum(1 for x in out if x["status"] == "Ошибка")
            tot = sum(x["secs"] or 0 for x in out)
            return self._j({"rows": out, "total": len(out), "done": done, "failed": bad,
                            "summary": "Пакетный режим, %d прогонов — %d успешно, %d с ошибкой, "
                                       "%.1f с суммарно" % (len(out), done, bad, tot),
                            "secs_total": round(tot, 1), "error": None})
        elif p == "/wiz_setg":
            # ТАБЛИЦА НАСТРОЕК ДОМА — по образцу B&W (конспект 17, §4 «Окно настроек
            # SMARTUpdate»): Option | Value | Status | Description, вкладки, кнопки
            # Default values / Discard changes / Apply. Раньше витрина не показывала
            # настройки вообще — только счётчики.
            # ВНИМАНИЕ: вход уже проверен выше (`cl = self._client(b)`). Дубль проверки по
            # заголовку X-Token ломал маршрут: фронт шлёт токен в ТЕЛЕ, а не в заголовке,
            # и живой запрос возвращал «нужен вход» при верном токоне (03.10.2026).
            import settings as _st
            try:
                # ЖИВОЙ источник — `_st.REGISTRY` (пространство, ключ, название, тип,
                # умолчание, описание, в_UI) плюс фактическое значение из config.json.
                # Метода `settings.all()` в доме НЕТ — звать его было бы выдумкой.
                _d = _st._raw()
            except Exception as _se:
                return self._j({"error": "настройки не прочитались: %s" % _se, "rows": []})
            _rows = []
            for _space, _k, _nm, _typ, _dfl, _desc, _ui in _st.REGISTRY:
                _val = _d.get(_k, _dfl)
                _rows.append({"space": _space, "option": _k, "name": _nm, "type": _typ,
                              "value": ("••••••" if "password" in str(_k) else _val),
                              "default": _dfl, "desc": _desc,
                              "changed": _k in _d and _d.get(_k) != _dfl,
                              "personal": _k in _st.PERSONAL_KEYS, "in_ui": bool(_ui)})
            return self._j({"rows": _rows, "count": len(_rows),
                            "changed": sum(1 for x in _rows if x["changed"]),
                            "spaces": sorted({x["space"] for x in _rows}), "error": None})
        elif p == "/wiz_run_gui":
            # ЖИВАЯ ПРАВКА ВИТРИНЫ 03.10.2026 (слово владельца: «в основном окне должен быть
            # другой дизайн и другой вызов окон»): раньше окна программ запускались ТОЛЬКО
            # руками — bat надо было знать и искать. Теперь витрина запускает окно сама.
            # Правила: имя программы сверяется со СПИСКОМ НА ДИСКЕ (никакого произвольного
            # запуска команд из запроса — иначе маршрут станет дырой), окно стартует
            # ОТДЕЛЬНЫМ процессом и НЕ блокирует агента, результат пишется в общий журнал.
            import glob as _glb
            import subprocess as _spp
            _agent_dir = os.path.dirname(os.path.abspath(__file__))
            _skip = ("backup", "_legacy", "_disabled", "__pycache__")
            _bats = {}
            for _b in _glb.glob(os.path.join(_agent_dir, "*", "*gui*.bat")):
                _rel = os.path.relpath(_b, _agent_dir)
                if any(("\\%s\\" % s) in _rel or _rel.startswith("%s\\" % s) for s in _skip):
                    continue
                _name = os.path.splitext(os.path.basename(_b))[0].replace("_gui", "")
                _bats.setdefault(_name, _b)
            for _nm2, _fn2 in (("harvest", "harvest_gui.py"), ("purge", "purge_gui.py")):
                _p2 = os.path.join(_agent_dir, _fn2)
                if os.path.isfile(_p2):
                    _bats.setdefault(_nm2, _fn2)
            if p == "/wiz_run_gui" and b.get("list") == "true":
                return self._j({"programs": sorted(_bats.keys()), "count": len(_bats),
                                "error": None})
            _want = (b.get("program") or "").strip()
            if not _want:
                return self._j({"error": "укажите program"}, 400)
            if _want not in _bats:
                return self._j({"error": "нет такого окна: %s (доступно: %s)"
                                % (_want, ", ".join(sorted(_bats)))}, 400)
            _target = _bats[_want]
            try:
                if _target.endswith(".bat"):
                    _proc = _spp.Popen(["cmd", "/c", os.path.basename(_target)],
                                        cwd=os.path.dirname(_target),
                                        creationflags=getattr(_spp, "CREATE_NO_WINDOW", 0))
                else:
                    _proc = _spp.Popen([sys.executable, "-X", "utf8", _target], cwd=_agent_dir,
                                       creationflags=getattr(_spp, "CREATE_NO_WINDOW", 0))
            except Exception as _rp_e:
                return self._j({"error": "не запустил %s: %s" % (_want, _rp_e)}, 500)
            try:
                log("витрина: запущено окно %s (PID %s)" % (_want, _proc.pid))
            except Exception:
                pass
            return self._j({"ok": True, "program": _want, "pid": _proc.pid,
                            "msg": "окно «%s» запущено (PID %s)" % (_want, _proc.pid)})
        elif p == "/setname":
            okf, msg = users.update_display_name(cl, b.get("name"))
            self._j({"ok": okf, "msg": msg})
        elif p == "/setpw":
            okf, msg = users.change_password(cl, b.get("old") or "", b.get("new") or "")
            self._j({"ok": okf, "msg": msg})
        elif p == "/chat/send":
            self._j(chat_tools.chat_send(cl, b.get("text")))
        elif p == "/chat/poll":
            self._j({"msgs": chat_tools.chat_poll(b.get("last") or 0)})
        elif p == "/admin/users":
            if not users.can_manage_users(cl):
                self._j({"error": "нет прав"}, 403); return
            op = b.get("op")
            if op == "list":
                self._j({"users": users.list_users(), "roles": users.ROLES})
            elif op == "role":
                okf, msg = users.admin_set_role(b.get("login") or "", b.get("role") or "")
                self._j({"ok": okf, "msg": msg})
            elif op == "add":
                okf = users.add_user(b.get("login") or "", b.get("pw") or b.get("password") or "", b.get("role") or "Инженер")
                self._j({"ok": okf, "msg": "создан" if okf else "логин занят или пустой"})
            elif op == "delete":
                lg = (b.get("login") or "").strip()
                if not lg:
                    self._j({"ok": False, "msg": "логин пустой"}, 400); return
                if lg == cl:
                    self._j({"ok": False, "msg": "нельзя удалить самого себя"}, 400); return
                us = users.list_users()
                tgt = [x for x in us if x.get("login") == lg]
                if not tgt:
                    self._j({"ok": False, "msg": "логин %s не найден" % lg}, 404); return
                adm = [x for x in us if x.get("role") == "Администратор" and x.get("login") != lg]
                if tgt[0].get("role") == "Администратор" and not adm:
                    self._j({"ok": False, "msg": "нельзя удалить последнего администратора"}, 400); return
                okf = users.admin_delete_user(lg)
                self._j({"ok": okf, "msg": ("пользователь %s удалён" % lg) if okf else "ошибка удаления"})
            elif op == "resetpw":
                okf, msg = users.admin_reset_password(b.get("login") or "", b.get("pw") or b.get("password") or "")
                self._j({"ok": okf, "msg": msg})
            else:
                self._j({"error": "неизвестная op"}, 400)
        else:
            self._j({"error": "не знаю"}, 404)

