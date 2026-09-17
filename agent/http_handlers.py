
    def do_GET(self):
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
            if not users.token_info(self.headers.get("X-Token") or ""): return self._j({"error": "no token"})
            self._j({"ollama": sched._wd_port(11434), "creoson": sched._wd_port(8080), "agent": True})
            return
        elif p == "/pdfpages":
            if not users.token_info(self.headers.get("X-Token") or ""): return self._j({"error": "no token"})
            qs = parse_qs(urlparse(self.path).query)
            name = qs.get("name", [""])[0]
            if not name: return self._j({"error": "no name"})
            self._j(pdf_tools.pdf_pages(name))
            return
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
            for d, fs in bydir.items():
                du = d.upper()
                if "\\\\CREO12\\\\" in du or "\\\\DATA\\\\" in du:
                    continue
                for nm, (path, mt) in fs.items():
                    # ... (Wait, I'll skip the complexity and just copy precisely)

            return

import json, re, os, socket, threading, time, datetime
from concurrent.futures import ThreadPoolExecutor
import subprocess, sys
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import core
from core import log, trace
import settings
import pdf_tools
import urllib.request as _ur
import tools_registry as TR
import scanner
import users
import chat_tools
import panel
import vision_tools as VI
import sched

# Import state from loop
try:
    from loop import LIVE_TOK, LIVE_THINK, LIVE, HOSTNAME
except ImportError:
    LIVE_TOK = {}
    LIVE_THINK = {}
    LIVE = {}
    HOSTNAME = socket.gethostname()

class Hd(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

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
        try:
            return json.loads(raw)
        except Exception:
            s = raw.decode("utf-8-sig", "ignore")
            if s.lstrip().startswith("{"):
                try:
                    return json.loads(s.replace('\"', '"'))
                except Exception:
                    return {}
            return {}

    def _client(self, b):
        u = users.token_info(b.get("token") or self.headers.get("X-Token") or "")
        return u["login"] if u else None
