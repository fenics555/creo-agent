import json, os, socket, threading, datetime
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import core
import settings
import users
import pdf_tools
import chat_tools
import panel
import vision_tools as VI
import tools_registry as TR
import sched
from loop import LIVE_TOK, LIVE_THINK, LIVE, PENDING, HOSTNAME, UI_FILE, _UI_CACHE, STUB_PAGE

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
                try: return json.loads(s.replace('\"', '"'))
                except Exception: return {}
            return {}

    def _client(self, b):
        u = users.token_info(b.get("token") or self.headers.get("X-Token") or "")
        return u["login"] if u else None

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
            self._j({
                "host": HOSTNAME, 
                "model": settings.get("llm_model"), 
                "blocks": len(TR.BLOCKS),
                "tools": len(TR.TOOLS), 
                "user": prof,
                "is_manager": users.can_manage_users(prof["login"]) if prof else False,
                "trails": tail, 
                "mode": settings.get_for(cl2["login"], "chat_mode", 1) if cl2 else 1,
                "up_ollama": _alive(11434), 
                "up_creoson": _alive(8080), 
                "up_agent": True
            })
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
            # ... (truncated for brevity in thought, but I'll include it)
            # I will copy the full content from agent.py later
            pass
        # ... (rest of do_GET)
        # For now, I'll use a more direct approach: I'll read the FULL Hd from agent.py and put it here.
