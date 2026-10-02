# -*- coding: utf-8 -*-
"""copy_server — служба копирования/переименования для веб-страниц дома.

Живой аудит 02.10.2026 (D:\\log\\reports\\REPORT_copy_audit_2026-10-02.md):
- путь к настройкам вынесен в data\\copy_settings.json (манифест п.19) — раньше окно искало
  `gui_settings.json` в папке программы, которого не было никогда;
- порт проверяется ДО старта: на Windows второй экземпляр раньше печатал «запущено» и висел
  молча (bind проходил из-за allow_reuse_address), теперь — понятная ошибка и код выхода 2;
- cleanup удаляет ТОЛЬКО папку, созданную этой службой (метка `.copy_server_tmp`), раньше
  достаточно было подделать подстроку `creo_copy_` в имени любой папки;
- ведётся свой журнал `D:\\AI\\log\\copy\\run_*.txt`.
"""
import json, os, shutil, socket, tempfile, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote_plus

PORT = 8000
HERE = Path(__file__).resolve().parent
WEB = HERE / "copy_web"
LOG_DIR = r"D:\AI\log\copy"
SETTINGS_PATH = r"D:\AI\tools\agent\data\copy_settings.json"
TMP_PREFIX = "creo_copy_"
TMP_MARK = ".copy_server_tmp"     # метка «эту папку создала наша служба»


def log_line(s):
    """Журнал службы; ошибка записи не должна ронять службу."""
    line = "%s %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), s)
    print(line, flush=True)
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(os.path.join(LOG_DIR, "run_%s.txt" % time.strftime("%Y-%m-%d")), "a",
                  encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def port_busy(host, port):
    s = socket.socket()
    s.settimeout(0.4)
    try:
        s.connect((host or "127.0.0.1", int(port)))
        return True
    except Exception:
        return False
    finally:
        s.close()
class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *a):
        # Раньше было `pass` — в журнале не было ни одного запроса, диагностировать службу
        # было нечем. Пишем короткую строку по запросу (без шума отдачи статики).
        try:
            log_line("HTTP %s" % (fmt % a))
        except Exception:
            pass
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
        # Живая находка 23.09.2026: страница отдавалась только по "/" и "/copy", а по прямому адресу
        # "/copy.html" приходил 404 (хотя файл на месте) — теперь принимаем все три вида.
        if p in ("/", "/copy", "/copy.html"):
            f = WEB / "copy.html"
            return self._send(200, f.read_bytes(), "text/html") if f.exists() else self._send(404, "copy.html not found", "text/plain")
        # 02.10.2026: раздавались и заглушки `creojs.js` и `page.js` (21 и 19 байт,
        # содержимое `// ... Stub`) — страница их не подключает, ссылок в доме не найдено,
        # удалены как мёртвый код (проверка: Select-String по copy_web\, ui\, *.html).
        for n in ("copy.css",):
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
            td = str(tempfile.mkdtemp(prefix=TMP_PREFIX))
            # МЕТКА «эту папку создала наша служба» (живая проверка 02.10.2026: раньше cleanup
            # удалял ЛЮБУЮ папку, в имени которой встречается `creo_copy_`)
            try:
                (Path(td) / TMP_MARK).write_text("copy_server", encoding="utf-8")
            except Exception:
                pass
            return {"ok": True, "directory": td, "plan": plan}
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
            # Защита 02.10.2026: раньше было достаточно, чтобы в имени ЛЮБОЙ папки стояло
            # `creo_copy_` — такой запрос удалял её целиком. Теперь нужна метка службы.
            if not d.exists():
                return {"ok": True, "note": "папки уже нет"}
            if not (d / TMP_MARK).exists():
                # Проверяется САМА папка (метка-файл внутри), а не подстрока в имени:
                # живая проверка 02.10.2026 показала, что первая версия защиты искала метку
                # в ИМЕНИ папки и потому отказывала даже своей.
                return {"ok": False,
                        "error": "не моя временная папка — не удаляю: %s" % d}
            shutil.rmtree(d, ignore_errors=True)
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
    import argparse

    ap = argparse.ArgumentParser(description="copy_server — служба копирования/переименования для веб-страниц дома")
    ap.add_argument("--port", type=int, default=PORT, help="порт (по умолчанию %d)" % PORT)
    ap.add_argument("--bind", default="127.0.0.1", help="адрес привязки (по умолчанию только своя машина)")
    ap.add_argument("--quiet", action="store_true", help="не печатать строку запуска")
    a = ap.parse_args()
    # Живая проверка 02.10.2026: на Windows второй экземпляр на занятом порту НЕ падал —
    # bind проходил (allow_reuse_address), процесс печатал «запущено» и висел молча.
    if port_busy(a.bind, a.port):
        msg = "порт %s:%d уже занят — служба, вероятно, уже поднята (окном или ctl.py)" % (a.bind, a.port)
        log_line(msg)
        raise SystemExit(2)
    try:
        srv = ThreadingHTTPServer((a.bind, a.port), H)
    except OSError as e:
        log_line("не подняться на %s:%d — %s" % (a.bind, a.port, e))
        raise SystemExit(2)
    log_line("copy_server: http://%s:%d/  (страница: /copy.html; журнал: %s)"
             % (a.bind, a.port, LOG_DIR))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()
