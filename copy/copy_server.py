# -*- coding: utf-8 -*-
import json, shutil, tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote_plus
PORT = 8000
WEB = Path(__file__).resolve().parent / "copy_web"
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers(); self.wfile.write(data)
    def _frame(self, payload):
        html = "<html><body><script>parent.postMessage({source:'creo-specification-pdf',payload:%s},'*');</script></body></html>" % json.dumps(payload)
        self._send(200, html, "text/html")
    def do_GET(self):
        p = self.path.split("?")[0]
        if p in ("/", "/copy"):
            f = WEB / "copy.html"
            return self._send(200, f.read_bytes(), "text/html") if f.exists() else self._send(404, "copy.html not found", "text/plain")
        for n in ("creojs.js", "page.js", "copy.css"):
            if p == "/" + n:
                f = WEB / n
                if f.exists():
                    return self._send(200, f.read_bytes(), "text/javascript" if n.endswith(".js") else "text/css")
        return self._send(404, "not found", "text/plain")
    def do_POST(self):
        ln = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(ln).decode("utf-8", "ignore")
        if raw.startswith("{"):
            try: v = json.loads(raw)
            except Exception: v = {}
        else:
            q = parse_qs(raw); v = {k: unquote_plus(q[k][0]) for k in q}
        p = self.path.split("?")[0]
        try:
            if p == "/api/assembly-copy-workspace-frame": r = self._ws(v)
            elif p == "/api/rename-copies-frame": r = self._copies(v)
            elif p == "/api/save-rename-graph-frame": r = self._graph(v, True)
            elif p == "/api/load-rename-graph-frame": r = self._graph(v, False)
            else: r = {"ok": False, "error": "unknown " + p}
        except Exception as e:
            r = {"ok": False, "error": str(e)}
        self._frame(r)
    def _ws(self, v):
        a = v.get("action")
        if a == "prepare":
            src = Path(v.get("source", ""))
            dst = Path(v.get("target", ""))
            if not src.exists(): return {"ok": False, "error": "источник не найден"}
            plan = []
            for f in src.iterdir():
                if f.is_file():
                    new_name = f.stem + "_copy" + f.suffix
                    plan.append({"old": f.name, "new": new_name})
            return {"ok": True, "directory": str(tempfile.mkdtemp(prefix="creo_copy_")), "plan": plan}
        if a == "collect":
            src, dst = Path(v.get("source", "")), Path(v.get("target", ""))
            items = json.loads(v.get("names") or "[]")
            cp, oc, mi = [], [], []
            for item in items:
                if isinstance(item, dict):
                    n_old, n_new = item.get("old"), item.get("new")
                    s, d = src / n_old, dst / n_new
                else:
                    n = item
                    s, d = src / n, dst / n
                if not s.exists(): mi.append(str(s)); continue
                if d.exists(): oc.append(str(d)); continue
                shutil.copy2(s, d); cp.append(str(d))
            return {"ok": True, "copied": cp, "occupied": oc, "missing": mi}
        if a == "cleanup":
            d = Path(v.get("directory", ""))
            if d.exists() and "creo_copy_" in d.name: shutil.rmtree(d, ignore_errors=True)
            return {"ok": True}
        return {"ok": False, "error": "bad action"}
    def _copies(self, v):
        f = Path(v.get("directory", "")) / "rename_copies.json"
        e = []
        if f.exists():
            try: e = json.loads(f.read_text(encoding="utf-8"))
            except Exception: e = []
        if v.get("action") == "append":
            try: x = json.loads(v.get("entry") or "{}")
            except Exception: x = {}
            if x: e.append(x)
            f.write_text(json.dumps(e, ensure_ascii=False, indent=1), encoding="utf-8")
        return {"ok": True, "entries": e, "path": str(f)}
    def _graph(self, v, save):
        f = Path(v.get("directory", "")) / "rename_graph.json"
        if save:
            f.write_text(v.get("graph") or "{}", encoding="utf-8"); return {"ok": True, "path": str(f)}
        return {"ok": True, "found": f.exists(), "graph": (json.loads(f.read_text(encoding="utf-8")) if f.exists() else None)}
if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
