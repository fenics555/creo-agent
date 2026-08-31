# -*- coding: utf-8 -*-
r"""
АГЕНТ v12 — ctl.py: единый пуск/стоп/сторож стека (Ollama, CREOSON, агент).
up [--browser] [--hidden] — идемпотентный пуск: поднимает ТОЛЬКО недостающее, живое не трогает.
down — явный стоп (агент, ollama-wd, creoson). restart — down+up. status — таблица портов.
--watch — сторож: раз в 60 сек тихо поднимает недостающее (никого не убивает).
"""
import os, sys, time, socket, subprocess, datetime

TOOLS = r"D:\AI\tools"
AG = TOOLS + r"\agent"
CREOSON_DIR = r"D:\AI\creoson\CreosonServer-3.0.2-win64"
LOG = TOOLS + r"\startup.log"

def log(line):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (datetime.datetime.now().strftime("%H:%M:%S"), line))
    except Exception: pass
    print(line)

def alive(port):
    try:
        s = socket.create_connection(("127.0.0.1", port), timeout=1); s.close(); return True
    except Exception: return False

def wait_port(port, sec):
    t = 0
    while t < sec:
        if alive(port): return True
        time.sleep(2); t += 2
    return False

def kill_pid(pidf):
    try:
        pid = open(pidf).read().strip()
        if pid: subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True)
    except Exception: pass
    try: os.remove(pidf)
    except Exception: pass

def start_ollama():
    wd = TOOLS + r"\OLLAMA-WD.bat"
    if os.path.exists(wd):
        subprocess.Popen('cmd /c start "" /B "%s"' % wd, shell=True)
    else:
        subprocess.Popen('cmd /c start "" /B ollama serve', shell=True)

def start_creoson():
    subprocess.Popen('cmd /c start "" /B /D "%s" creoson_run.bat' % CREOSON_DIR, shell=True)

def start_agent(hidden):
    if hidden:
        subprocess.Popen('powershell -NoProfile -WindowStyle Hidden -Command "cmd /c cd /d %s && python agent.py >> %s\\agent_console.log 2>&1"' % (AG, TOOLS), shell=True)
    else:
        subprocess.Popen('start "АГЕНТ v12" cmd /k "cd /d %s && python agent.py"' % AG, shell=True)

def up(browser=False, hidden=False):
    log("== ctl up ==")
    if alive(11434): log("Ollama уже на 11434")
    else:
        log("поднимаю Ollama..."); start_ollama()
        log("Ollama на 11434" if wait_port(11434, 60) else "ВНИМАНИЕ: Ollama не поднялась за 60 сек")
    if alive(8080): log("CREOSON уже на 8080")
    else:
        log("поднимаю CREOSON..."); start_creoson()
        log("CREOSON на 8080" if wait_port(8080, 60) else "ВНИМАНИЕ: CREOSON не поднялся за 60 сек")
    if alive(8765): log("агент уже на 8765")
    else:
        kill_pid(AG + r"\agent.pid")
        log("поднимаю агента..."); start_agent(hidden)
        log("агент на 8765" if wait_port(8765, 60) else "ВНИМАНИЕ: агент не поднялся за 60 сек")
    if browser:
        subprocess.Popen('cmd /c start "" http://192.168.88.159:8765', shell=True)

def down():
    log("== ctl down ==")
    kill_pid(AG + r"\agent.pid")
    kill_pid(TOOLS + r"\ollama_wd.pid")
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Get-CimInstance Win32_Process -Filter \"name='java.exe'\" | Where-Object { $_.CommandLine -like '*creoson*' } | ForEach-Object { $_.Terminate() }"],
                   capture_output=True)
    log("стоп завершён")

def status():
    for name, port in (("Ollama", 11434), ("CREOSON", 8080), ("агент", 8765)):
        print("%-8s %-6s %s" % (name, port, "жив" if alive(port) else "МЁРТВ"))

def watch():
    log("== ctl watch старт ==")
    while True:
        try:
            if not (alive(11434) and alive(8080) and alive(8765)):
                up(browser=False, hidden=True)
        except Exception as e:
            log("watch err: %s" % e)
        time.sleep(60)

if __name__ == "__main__":
    a = sys.argv[1:]
    if "--watch" in a: watch()
    elif "up" in a: up("--browser" in a, "--hidden" in a)
    elif "down" in a: down()
    elif "restart" in a: down(); up("--browser" in a)
    elif "status" in a: status()
    else: print(__doc__)