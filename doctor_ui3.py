# -*- coding: utf-8 -*-
import io
cp = r"D:\AI\tools\agent\ctl.py"
lines = io.open(cp, encoding="utf-8").read().splitlines(True)
out, changed = [], False
for ln in lines:
    if "powershell -NoProfile -WindowStyle Hidden" in ln and "agent.py" in ln:
        ind = ln.index("subprocess.Popen")
        ln = ln[:ind] + "subprocess.Popen('cmd /c cd /d %s && python agent.py >> %sagent_console.log 2>&1' % (AG, TOOLS), shell=True, creationflags=0x08000000)\n"
        changed = True
    out.append(ln)
if changed:
    io.open(cp, "w", encoding="utf-8").write("".join(out))
    print("[+] строка hidden заменена на CREATE_NO_WINDOW")
else:
    print("[~] такой строки нет (уже починено?)")