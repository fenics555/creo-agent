# -*- coding: utf-8 -*-
import io
ap = r"D:\AI\tools\agent\spec_tools.py"
s = io.open(ap, encoding="utf-8").read()
old = '''def _creoson(session, command, function, data=None):
    body = {"command": command, "function": function, "data": data or {}}
    if session:
        body["sessionId"] = session
    try:
        r = core.post("http://127.0.0.1:8080/creoson", body, t=60)
    except Exception as e:
        return {"status": {"error": True, "message": str(e)}}
    return r'''
new = '''def _creoson(session, command, function, data=None):
    import urllib.request
    body = {"command": command, "function": function, "data": data or {}}
    if session:
        body["sessionId"] = session
    req = urllib.request.Request("http://127.0.0.1:8080/creoson",
                                 data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"status": {"error": True, "message": str(e)}}'''
if new in s: print("[~] уже")
elif old in s:
    s = s.replace(old, new, 1)
    io.open(ap, "w", encoding="utf-8").write(s)
    print("[+] creoson напрямую")
else: print("[x] якорь не найден")