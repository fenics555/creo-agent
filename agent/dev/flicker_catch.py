# -*- coding: utf-8 -*-
r"""ЛОВУШКА МОРГАНИЯ: 3 минуты пишем (1) смену активного окна и (2) появление процессов.
Цель: поймать, ЧТО именно вспыхивает (живая находка 24.09.2026 — хозяин просил починить моргание)."""
import ctypes, subprocess, time, datetime, traceback
from pathlib import Path

OUT = Path(r"D:\AI\log\reports\flicker_catch.txt")
u32 = ctypes.windll.user32
NAMES = ("cmd", "conhost", "wscript", "cscript", "powershell", "pwsh", "java", "xtop",
         "parametric", "ollama", "msedge", "browser", "yandex", "python", "pythonw", "wermgr", "WerFault")
log = []


def fg():
    try:
        h = u32.GetForegroundWindow()
        n = u32.GetWindowTextLengthW(h)
        b = ctypes.create_unicode_buffer(n + 2)
        u32.GetWindowTextW(h, b, n + 2)
        pid = ctypes.c_ulong()
        u32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        return b.value, pid.value
    except Exception:
        return "?", 0


def proc_set():
    try:
        out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True,
                             creationflags=0x08000000, timeout=15)
        s = {}
        for line in (out.stdout or "").splitlines():
            p = line.split('","')
            if len(p) >= 2:
                nm = p[0].strip('"').lower().replace(".exe", "")
                pid = p[1].strip('"')
                if nm in NAMES:
                    s[pid] = nm
        return s
    except Exception:
        return {}


try:
    t0 = time.time()
    prev_w = fg()
    prev_p = proc_set()
    log.append("старт наблюдения %s (окно: %r)" % (datetime.datetime.now().strftime("%H:%M:%S"), prev_w[0]))
    while time.time() - t0 < 180:
        w = fg()
        if w != prev_w:
            log.append("%s ОКНО -> %r (pid %s)" % (datetime.datetime.now().strftime("%H:%M:%S"), w[0][:70], w[1]))
            prev_w = w
        p = proc_set()
        new = {k: v for k, v in p.items() if k not in prev_p}
        gone = {k: v for k, v in prev_p.items() if k not in p}
        if new or gone:
            if new:
                log.append("%s ПОЯВИЛИСЬ: %s" % (datetime.datetime.now().strftime("%H:%M:%S"),
                                                ", ".join(sorted(new.values()))))
            if gone:
                log.append("%s ЗАКРЫЛИСЬ: %s" % (datetime.datetime.now().strftime("%H:%M:%S"),
                                                ", ".join(sorted(gone.values()))))
            prev_p = p
        time.sleep(0.25)
    log.append("конец наблюдения (%d строк событий)" % len(log))
except Exception:
    log.append("ОШИБКА:\n" + traceback.format_exc())
OUT.write_text("\n".join(log), encoding="utf-8")
print("ok")
