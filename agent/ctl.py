# -*- coding: utf-8 -*-
"""АГЕНТ v15 — ctl.py: единый пуск/стоп/сторож стека (Ollama, CREOSON, агент).
up [--browser] [--hidden] — идемпотентный пуск: поднимает ТОЛЬКО недостающее.
down — явный стоп. restart — down+up. status — таблица портов. --watch — сторож 60 сек."""
import os, sys, time, socket, subprocess, datetime, shutil, webbrowser

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

# ==== БЕЗОКОННЫЙ ЗАПУСК (23.11.2026 — слово владельца «моргают окна PowerShell, надоело») ====
# Причина моргания: up() поднимал процессы через `powershell Start-Process ... -WindowStyle Hidden`
# и `cmd /c start`. Окно консоли при таком пути всё равно создаётся и мигает.
# МЕТОД ЗАМЕНЁН: pythonw.exe (окна не создаёт вовсе) + DETACHED_PROCESS + CREATE_NO_WINDOW,
# вывод пишется в файлы data\tmp\<имя>_out.txt / _err.txt. PowerShell и окна из пути убраны.
_PYW = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
if not os.path.exists(_PYW):
    _PYW = sys.executable
_NW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
_DET = getattr(subprocess, "DETACHED_PROCESS", 0x00000008)


def _spawn(argv, cwd, name):
    r"""Запуск БЕЗ окна: своя сессия, потоки в файл D:\AI\log\agent (культура дома)."""
    tmp = os.path.join(os.path.dirname(TOOLS), "log", "agent")
    os.makedirs(tmp, exist_ok=True)
    out = open(os.path.join(tmp, name + "_out.txt"), "ab")
    err = open(os.path.join(tmp, name + "_err.txt"), "ab")
    try:
        return subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL,
                                stdout=out, stderr=err,
                                creationflags=_NW | _DET, close_fds=True)
    finally:
        out.close()
        err.close()


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
    # 23.11.2026: без окна — ollama.exe напрямую (прежний `cmd /c start` создавал консоль).
    exe = shutil.which("ollama") or r"C:\Users\User\AppData\Local\Programs\Ollama\ollama.exe"
    _spawn([exe, "serve"], TOOLS, "ollama")


def start_creoson():
    # bat нужен (setvars Creoson), но окна не будет: cmd живёт в невидимой сессии (_spawn).
    _spawn(["cmd", "/c", "creoson_run.bat"], CREOSON_DIR, "creoson")


def start_copyserver():
    _spawn([_PYW, os.path.join("copy", "copy_server.py")], AG, "copy")


def start_agent(hidden=True):
    # 23.11.2026: агент ВСЕГДА без окна (pythonw) — окна консоли больше не открываются.
    # Состояние смотреть: `python ctl.py status` и data\tmp\agent_err.txt.
    _spawn([_PYW, "agent.py"], AG, "agent")


def verify_agent():
    """Приёмка подъёма агента (живая проверка 02.10.2026). Долг Б10 из отчёта
    «после ctl up порт пропадал» НЕ воспроизводится (2 прогона подряд — порт держится),
    поэтому вместо правки вслепую добавлена проверка: если агент не поднялся,
    ctl.py сам печатает ПРИЧИНУ из stderr агента, а не молчит."""
    pid = 0
    try:
        pid = int(open(AG + r"\agent.pid").read().strip() or 0)
    except Exception:
        pass
    if not alive(8765):
        return False, "порт 8765 не слушается (agent.pid=%s)" % pid
    if not pid:
        return False, "порт слушается, но agent.pid пуст — нечем управлять"
    # PID из файла должен совпадать с живым процессом, который держит порт
    out = ""
    try:
        for _p in subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                                 errors="replace", timeout=20).stdout.splitlines():
            if ":8765" in _p and "LISTENING" in _p:
                out = _p.split()[-1]
                break
    except Exception:
        out = ""
    if out and out.isdigit() and int(out) != pid:
        return False, "порт держит процесс %s, а в agent.pid %s — не совпадают" % (out, pid)
    return True, "порт 8765 держит PID %s (совпадает с agent.pid)" % pid


def agent_stderr_tail(n=8):
    """Хвост stderr агента — чтобы отказ был виден, а не загадочен."""
    for f in (AG + r"\data\tmp\agent_err.txt", AG + r"\data\tmp\agent_out.txt"):
        try:
            txt = open(f, encoding="utf-8", errors="replace").read().strip().splitlines()
            if txt:
                return "%s: %s" % (os.path.basename(f), " / ".join(txt[-n:]))
        except Exception:
            continue
    return "stderr агента пуст"


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
        if wait_port(8765, 60):
            ok, why = verify_agent()
            log("агент на 8765 — %s" % why if ok else "ВНИМАНИЕ: %s" % why)
            if not ok:
                log("хвост вывода агента: %s" % agent_stderr_tail())
        else:
            log("ВНИМАНИЕ: агент не поднялся за 60 сек")
            log("хвост вывода агента: %s" % agent_stderr_tail())
    if browser:
        webbrowser.open("http://%s:8765" % socket.gethostname())


def down():
    log("== ctl down ==")
    kill_pid(AG + r"\agent.pid")
    kill_pid(TOOLS + r"\ollama_wd.pid")
    # 23.11.2026: без PowerShell — PID CREOSON ищем по порту 8080 и снимаем taskkill (без окна).
    try:
        for _l in subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                                 errors="replace", timeout=20).stdout.splitlines():
            if ":8080" in _l and "LISTENING" in _l:
                _pid = _l.split()[-1]
                subprocess.run(["taskkill", "/PID", _pid, "/F"], capture_output=True)
                log("CREOSON снят по PID %s" % _pid)
                break
    except Exception as e:
        log("down: CREOSON не снят (%s)" % e)
    log("стоп завершён")


def status():
    for name, port in (("Ollama", 11434), ("CREOSON", 8080), ("агент", 8765), ("copy", 8000)):
        print("%-8s %-6d %s" % (name, port, "жив" if alive(port) else "МЁРТВ"))
    ok, why = verify_agent()
    print("приёмка агента: %s — %s" % ("OK" if ok else "ПРОВАЛ", why))
    if not ok:
        print("хвост вывода агента: %s" % agent_stderr_tail())


def _kill_stray_agents():
    """66c P15/Q3: python agent.py с PID != содержимого agent.pid снимаются
    детерминированно (не по «старший/младший»): приёмка рестарта всегда
    сходится с профилактикой crash_agent-duplicate-restart-race.

    ПРАВКА 05.10.2026 (слово владельца «агент не запускается»; найдено чтением кода):
    гонка была в самом правиле. Агент пишет свой `agent.pid` УЖЕ ПОСЛЕ старта, поэтому в
    первые секунды запуска pid-файл ещё старый, а новый агент — «блуждающий». Сторож (AI-WATCH,
    каждые 60 с) в это окно убивал ЖИВОЙ агент через `taskkill /F`, а у того не срабатывает
    `atexit` — поэтому в журнале не оставалось ни строки (та сама «тихая смерть» крах-скилла).
    ПРАВИЛО: эталон жизни — ПОРТ, а не pid-файл. Если 8765 держит какой-то `agent.py`, он
    ЖИВОЙ, и его не трогаем ни при каких расхождениях с pid-файлом."""
    try:
        keep = int(open(AG + r"\agent.pid").read().strip() or 0)
    except Exception:
        keep = 0
    try:
        holder = 0
        for _p in subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                                 errors="replace", timeout=20).stdout.splitlines():
            if ":8765" in _p and "LISTENING" in _p:
                holder = int(_p.split()[-1])
                break
    except Exception:
        holder = 0
    # 23.11.2026: PowerShell и убийства убраны (мигали окнами и роняли живой агент).
    # Эталон жизни — ПОРТ: pid-файл подтягиваем к держателю 8765, чужие процессы не трогаем.
    if holder and holder != keep:
        try:
            with open(AG + r"\agent.pid", "w", encoding="utf-8") as f:
                f.write(str(holder))
            log("agent.pid подтянут к держателю порта 8765: %s" % holder)
        except Exception as e:
            log("agent.pid не обновлён: %s" % e)


def watch():
    log("== ctl watch старт ==")
    fails = 0
    while True:
        try:
            if not (alive(11434) and alive(8765)):   # CREOSON не обязателен: он поднимается по требованию
                time.sleep(8)  # Q2 дебаунс: не махать up в окно ручного рестарта
                if not (alive(11434) and alive(8765)):
                    up(browser=False, hidden=True)
            if alive(8765):
                fails = 0
                _kill_stray_agents()  # Q3: pid-файл = держатель порта (без убийств)
            else:
                fails += 1
        except Exception as e:
            fails += 1
            log("watch err: %s" % e)
        # 23.11.2026 BACKOFF: агент падал на импорте, а сторож перезапускал его каждые ~70 с
        # (8911 записей «ctl up» в startup.log). Теперь 3 неудачи подряд = пауза 10 минут, одна строка.
        if fails >= 3:
            log("watch: %d неудач подряд — повтор через 10 минут" % fails)
            time.sleep(600)
            fails = 0
            continue
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