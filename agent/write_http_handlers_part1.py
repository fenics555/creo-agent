import json, os, socket, threading, datetime, re, subprocess, sys
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
from loop import LIVE_TOK, LIVE_THINK, LIVE, PENDING, HOSTNAME, UI_FILE, _UI_CACHE, STUB_PAGE, _SYS_CACHE, ask, do_approve

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
