# -*- coding: utf-8 -*-
"""АГЕНТ v15 — ctl.py: единый пуск/стоп/сторож стека (Ollama, CREOSON, агент).
up [--browser] [--hidden] — идемпотентный пуск: поднимает ТОЛЬКО недостающее.
down — явный стоп. restart — down+up. status — таблица портов. --watch — сторож 60 сек."""
import os, sys, time, socket, subprocess, datetime

# ==== СКРЫТИЕ КОНСОЛЬНЫХ ОКОН (живая находка 24.09.2026 — «моргает синим») ====
# Сторож дома (AI-WATCH -> pythonw ctl.py --watch) каждые 60 с вызывал _kill_stray_agents(),
# а тот запускал PowerShell БЕЗ CREATE_NO_WINDOW: на экране раз в минуту вспыхивало окно PowerShell.
# Патчим subprocess в СВОЁМ процессе: любой запуск из ctl.py идёт без окна.
if not getattr(subprocess, "_nw_patched", False) and hasattr(subprocess, "CREATE_NO_WINDOW"):
    _CNW = subprocess.CREATE_NO_WINDOW
    _P0, _R0 = subprocess.Popen, subprocess.run

    def _P_nw(*a, **kw):
        kw.setdefault("creationflags", _CNW)
        return _P0(*a, **kw)

    def _R_nw(*a, **kw):
        kw.setdefault("creationflags", _CNW)
        return _R0(*a, **kw)

    subprocess.Popen, subprocess.run = _P_nw, _R_nw
    subprocess._nw_patched = True


TOOLS = r"D:\AI\tools"
AG = TOOLS + r"\agent"


def _cfg(key, defl):
    try:
        import json as _j
        d = _j.load(open(TOOLS + r"\agent\data\config.json", encoding="utf-8"))
        return d.get(key) or defl
    except Exception:
        return defl


CREOSON_DIR = _cfg("creoson_dir", r"D:\PTC\CREO-LOCAL-SETUP\creoson")
LOG = TOOLS + r"\startup.log"


def log(line):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (datetime.datetime.now().strftime("%H:%M:%S"), line))
    except Exception:
        pass
    print(line)


def alive(port):
    try:
        s = socket.create_connection(("127.0.0.1", port), timeout=1); s.close(); return True
    except Exception:
        return False


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
    except Exception:
        pass
    try: os.remove(pidf)
    except Exception: pass


def start_ollama():
    # ОДНА МОДЕЛЬ НА ДОМ (24.09.2026): держим веса в памяти, вторую модель не грузим.
    os.environ.setdefault("OLLAMA_KEEP_ALIVE", "1h")
    os.environ.setdefault("OLLAMA_MAX_LOADED_MODELS", "1")
    wd = TOOLS + r"\OLLAMA-WD.bat"
    if os.path.exists(wd):
        subprocess.Popen('cmd /c start "" /B "%s"' % wd, shell=True)
    else:
        subprocess.Popen('cmd /c start "" /B ollama serve', shell=True)


def start_creoson():
    subprocess.Popen('cmd /c start "" /B /D "%s" creoson_run.bat' % CREOSON_DIR, shell=True)


def start_copyserver():
    os.makedirs(AG + r"\data\tmp", exist_ok=True)
    subprocess.Popen(["powershell", "-NoProfile", "-Command",
        "Start-Process python -ArgumentList 'copy\\copy_server.py' "
        "-WorkingDirectory '%s' -WindowStyle Hidden "
        "-RedirectStandardOutput '%s\\data\\tmp\\copy_out.txt' "
        "-RedirectStandardError '%s\\data\\tmp\\copy_err.txt'" % (AG, AG, AG)])


def start_agent(hidden):
    if hidden:
        os.makedirs(AG + r"\data\tmp", exist_ok=True)
        subprocess.Popen(["powershell", "-NoProfile", "-Command",
            "Start-Process python -ArgumentList 'agent.py' "
            "-WorkingDirectory '%s' -WindowStyle Hidden "
            "-RedirectStandardOutput '%s\\data\\tmp\\agent_out.txt' "
            "-RedirectStandardError '%s\\data\\tmp\\agent_err.txt'" % (AG, AG, AG)])
    else:
        subprocess.Popen('start "АГЕНТ v15" cmd /c "cd /d %s && python agent.py"' % AG, shell=True)


def up(browser=False, hidden=False):
    log("== ctl up ==")
    if alive(11434): log("Ollama уже на 11434")
    else:
        log("поднимаю Ollama..."); start_ollama()
        log("Ollama на 11434" if wait_port(11434, 60) else "ВНИМАНИЕ: Ollama не поднялась за 60 сек")
    # CREOSON убран из автозапуска 23.09.2026: он нужен только блокам на creo_call,
    # и поднимается по требованию (_ensure_creoson в creo_tools).
    if alive(8080):
        log("CREOSON уже на 8080")
    if alive(8000): log("copy-server уже на 8000")
    else:
        log("поднимаю copy-server..."); start_copyserver()
        log("copy-server на 8000" if wait_port(8000, 30) else "ВНИМАНИЕ: copy-server не поднялся")
    if alive(8765): log("агент уже на 8765")
    else:
        kill_pid(AG + r"\agent.pid")
        log("поднимаю агента..."); start_agent(hidden)
        log("агент на 8765" if wait_port(8765, 60) else "ВНИМАНИЕ: агент не поднялся за 60 сек")
    if browser:
        subprocess.Popen('cmd /c start "" http://%s:8765' % socket.gethostname(), shell=True)


def down():
    log("== ctl down ==")
    kill_pid(AG + r"\agent.pid")
    kill_pid(TOOLS + r"\ollama_wd.pid")
    subprocess.run(["powershell", "-NoProfile", "-Command",
        "Get-CimInstance Win32_Process -Filter \"Name='java.exe'\" | Where-Object { $_.CommandLine -like '*creoson*' } | ForEach-Object { $_.Terminate() }"],
        capture_output=True)
    log("стоп завершён")


def status():
    for name, port in (("Ollama", 11434), ("CREOSON", 8080), ("агент", 8765), ("copy", 8000)):
        print("%-8s %-6d %s" % (name, port, "жив" if alive(port) else "МЁРТВ"))


def _kill_stray_agents():
    """66c P15/Q3: python agent.py с PID != содержимого agent.pid снимаются
    детерминированно (не по «старший/младший»): приёмка рестарта всегда
    сходится с профилактикой crash_agent-duplicate-restart-race."""
    try:
        keep = int(open(AG + r"\agent.pid").read().strip() or 0)
    except Exception:
        keep = 0
    subprocess.run(["powershell", "-NoProfile", "-Command",
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
        "Where-Object { $_.CommandLine -like '*agent.py*' -and $_.ProcessId -ne %d } | "
        "ForEach-Object { taskkill /PID $_.ProcessId /F | Out-Null }" % keep],
        capture_output=True)


def watch():
    log("== ctl watch старт ==")
    while True:
        try:
            if not (alive(11434) and alive(8765)):   # CREOSON не обязателен: он поднимается по требованию
                time.sleep(8)  # Q2 дебаунс: не махать up в окно ручного рестарта
                if not (alive(11434) and alive(8765)):
                    up(browser=False, hidden=True)
            if alive(8765):
                _kill_stray_agents()  # Q3 дедуп: всё, что не в agent.pid
        except Exception as e:
            log("watch err: %s" % e)
        time.sleep(60)


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--watch" in a: watch()
    elif "creoson" in a:
        log("поднимаю CREOSON по команде..."); start_creoson()
        log("CREOSON на 8080" if wait_port(8080, 60) else "ВНИМАНИЕ: CREOSON не поднялся за 60 сек")
    elif "up" in a: up("--browser" in a, "--hidden" in a)
    elif "down" in a: down()
    elif "restart" in a: down(); up("--browser" in a, "--hidden" in a)
    elif "status" in a: status()
    else: print(__doc__)