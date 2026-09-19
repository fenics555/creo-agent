# -*- coding: utf-8 -*-
"""АГЕНТ v15 — http_handlers.py: HTTP-обработчики витрины (do_GET/do_POST)."""
import json, os, socket, threading, datetime, re, subprocess, sys
from urllib.parse import urlparse, parse_qs
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import core
print(core.LOGF)
from core import log, trace
import settings
import pdf_tools
import harvest_reader
import users
import chat_tools
import panel
import tools_registry as TR
import vision_tools as VI
from loop import (LIVE_TOK, LIVE_THINK, LIVE, PENDING, HOSTNAME, UI_FILE,
                  _UI_CACHE, STUB_PAGE, _SYS_CACHE, ask, do_approve)
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
    handler.send_header("Cache-Control", "no-cache")
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
        try:
            p = urlparse(self.path).path
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
                self._j({"host": HOSTNAME, "model": settings.get("llm_model"), "blocks": len(TR.BLOCKS),
                         "tools": len(TR.TOOLS), "user": prof,
                         "is_manager": users.can_manage_users(prof["login"]) if prof else False,
                         "trails": tail, "mode": settings.get_for(cl2["login"], "chat_mode", 1) if cl2 else 1,
                         "up_ollama": _alive(11434), "up_creoson": _alive(8080), "up_agent": True})
                return
            elif p == "/health":
                if not users.token_info(self.headers.get("X-Token") or ""): return self._j({"error": "no token"}, 401)
                self._j({"ollama": _wd_port(11434), "creoson": _wd_port(8080), "agent": True})
                return
            elif p == "/pdfpages":
                if not users.token_info(self.headers.get("X-Token") or ""): return self._j({"error": "no token"}, 401)
                qs = parse_qs(urlparse(self.path).query)
                name = qs.get("name", [""])[0]
                if not name: return self._j({"error": "no name"})
                self._j(pdf_tools.pdf_pages(name))
                return
            elif p == "/pdfstatus":
                if not users.token_info(self.headers.get("X-Token") or ""): return self._j({"error": "no token"}, 401)
                qs = parse_qs(urlparse(self.path).query)
                name = qs.get("name", [""])[0]
                if not name: return self._j({"error": "no name"})
                self._j(pdf_tools.pdf_status(name))
                return
            elif p == "/children":
                if not users.token_info(self.headers.get("X-Token") or ""): return self._j({"error": "no token"}, 401)
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
                if not users.token_info(self.headers.get("X-Token") or ""): return self._j({"error": "no token"}, 401)
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
                if not users.token_info(self.headers.get("X-Token") or ""): return self._j({"error": "no token"}, 401)
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
                if not users.token_info(self.headers.get("X-Token") or ""):
                    return self._j({"error": "no token"}, 401)
                from urllib.parse import parse_qs, urlparse
                qs = parse_qs(urlparse(self.path).query)
                root = qs.get("root", [None])[0]
                entries = harvest_reader.get_registry_entries(root_filter=root)
                self._j({"pairs": entries, "total": len(entries)})
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
                    self._j({"error": "ошибка рендеринга"})
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
            else:
                self._j({"error": "не знаю"}, 404)
        except Exception as e:
            import traceback
            err_msg = traceback.format_exc()
            print(f"CRASH in do_GET: {err_msg}")
            self._j({"error": str(e)}, 500)

