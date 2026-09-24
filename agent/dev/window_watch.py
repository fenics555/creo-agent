# -*- coding: utf-8 -*-
r"""ЛОВУШКА ОКОН (живая находка 24.09.2026 — хозяин просил починить «моргание синим»).
Каждые 0.25 с перечисляем ВСЕ видимые окна и пишем, какие появились/исчезли: класс окна + заголовок.
Консоль = ConsoleWindowClass, браузер = Chrome_WidgetWin_*, Creo = окно xtop и т.п.
Пишем сразу в файл (можно читать на ходу)."""
import ctypes, time, datetime, traceback
from ctypes import wintypes
from pathlib import Path

OUT = Path(r"D:\AI\log\reports\window_watch.txt")
u32 = ctypes.windll.user32
PROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)


def windows():
    res = {}

    def cb(h, _):
        try:
            if u32.IsWindowVisible(h):
                n = u32.GetWindowTextLengthW(h)
                b = ctypes.create_unicode_buffer(n + 2)
                u32.GetWindowTextW(h, b, n + 2)
                c = ctypes.create_unicode_buffer(256)
                u32.GetClassNameW(h, c, 256)
                res[int(h)] = (c.value, b.value.strip()[:70])
        except Exception:
            pass
        return True

    u32.EnumWindows(PROC(cb), 0)
    return res


def w(line):
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(line + "\n")


try:
    if OUT.exists():
        OUT.unlink()
    SECONDS = 300
    w("старт наблюдения %s (окон сейчас: %d)" % (datetime.datetime.now().strftime("%H:%M:%S"), len(windows())))
    prev = windows()
    t0 = time.time()
    while time.time() - t0 < SECONDS:
        cur = windows()
        for h, (cls, title) in cur.items():
            if h not in prev:
                w("%s ПОЯВИЛОСЬ окно: %-24s %r" % (datetime.datetime.now().strftime("%H:%M:%S"), cls, title))
        for h, (cls, title) in prev.items():
            if h not in cur:
                w("%s ЗАКРЫЛОСЬ окно: %-24s %r" % (datetime.datetime.now().strftime("%H:%M:%S"), cls, title))
        prev = cur
        time.sleep(0.25)
    w("конец наблюдения %s" % datetime.datetime.now().strftime("%H:%M:%S"))
except Exception:
    w("ОШИБКА:\n" + traceback.format_exc())
print("ok")