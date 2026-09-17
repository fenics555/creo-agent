content = """import json, re, os, socket, threading, time, datetime
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
                    return json.loads(s.replace('\\\"', '"'))
                except Exception:
                    return {}
            return {}

    def _client(self, b):
        u = users.token_info(b.get("token") or self.headers.get("X-Token") or "")
        return u["login"] if u else None
"""
with open(r"D:\AI\tools\agent\http_handlers.py", "w", encoding="utf-8") as f:
    f.write(content)
