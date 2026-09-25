# -*- coding: utf-8 -*-
r"""PLM Reader — автономный просмотр данных изделий из файлов CAD (детали, сборки, чертежи).

Кнопка «Сканировать» обходит выбранную папку и показывает таблицу:
Обозначение · Наименование · Материал · Объём (мм³) · Габарит · Роль/родитель · Ревизия · Дата · Пользователь.

Запуск:
    python plm_reader.py                            — окно
    python plm_reader.py --folder DIR               — без окна: таблица в консоль
    python plm_reader.py --folder DIR --csv out.csv — без окна: выгрузка в CSV

Зависимости: только стандартная библиотека Python (tkinter — для окна).
"""
import argparse
import csv
import datetime
import json
import os
import re
import struct
import sys
import threading

APP_TITLE = "PLM Reader"
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

DEFAULT_SETTINGS = {
    "folder": "",
    "max_size_mb": 24,
    "recurse": True,
    "columns": ["Обозначение", "Наименование", "Материал", "Объём, мм³",
                "Роль", "Родитель", "Ревизия", "Дата", "Пользователь", "Файл"],
}

MODELFILE = re.compile(r"\.([a-z_]{2,4})\.\d+$", re.IGNORECASE)


def read_bytes(path, limit_mb):
    if limit_mb and os.path.getsize(path) > limit_mb * 1_000_000:
        return None
    with open(path, "rb") as f:
        return f.read()


def sections(raw):
    """Внутреннее оглавление файла: {имя: (offset, length)}."""
    out, pos = {}, raw.find(b"#UGC_TOC")
    for _ in range(20):
        if pos < 0:
            break
        p = raw.find(b"\n", pos)
        nxt = -1
        while True:
            e = raw.find(b"\n", p + 1)
            if e < 0:
                break
            line = raw[p + 1:e].decode("ascii", "replace").strip()
            p = e
            if line.startswith("NEXT_TOC_ENTRY"):
                nxt = int(line.split()[1], 16)
                break
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_:]{1,40}) ([0-9a-f]{2,8}) ([0-9a-f]{2,8})"
                         r"(?: ([0-9a-f]{2,8}))?(.*)$", line)
            if m and (not m.group(5).strip() or m.group(5).strip()[0] in "0123456789-"):
                ln = int(m.group(4), 16) if m.group(4) else int(m.group(3), 16)
                out[m.group(1)] = (int(m.group(2), 16), max(ln, 1))
        if nxt < 0 or nxt >= len(raw):
            break
        pos = nxt
    return out


def real_value(raw, key):
    """Числовое поле изделия (объём, масса …). None, если не найдено."""
    m = re.search(rb"\xe0\x02" + re.escape(key.encode()) + rb"\x00\xed", raw)
    if not m or m.end() + 8 > len(raw):
        return None
    try:
        return struct.unpack(">d", raw[m.end():m.end() + 8])[0]
    except Exception:
        return None


def packed_at(raw, i):
    """Компактное число: (длина, значение) или None."""
    if i >= len(raw):
        return None
    b0 = raw[i]
    if b0 == 0x2D and i + 7 < len(raw):
        frac = raw[i + 3:i + 8]
        if all(0x20 <= x < 0x7F for x in frac):
            return None
        b1, b2 = raw[i + 1], raw[i + 2]
        E, F = b1 >> 4, ((b1 & 0x0F) << 8) | b2
        if E > 15:
            return None
        base = (2 ** (E + 1)) * (1 + F / 4096.0)
        step = (2 ** (E + 1)) / 4096.0
        return 8, base + (int.from_bytes(frac, "big") / float(1 << 40)) * step
    if b0 in (0x2F, 0x48) and i + 2 < len(raw):
        b1, b2 = raw[i + 1], raw[i + 2]
        E, F = b1 >> 4, ((b1 & 0x0F) << 8) | b2
        v = (2 ** (E + 1)) * (1 + F / 4096.0)
        return 3, (-v if b0 == 0x48 else v)
    if b0 == 0x2A and i + 2 < len(raw):
        b1, b2 = raw[i + 1], raw[i + 2]
        E, F = b1 >> 4, ((b1 & 0x0F) << 8) | b2
        return 3, (2 ** (E - 15)) * (1 + F / 4096.0)
    return None


def clean_name(s):
    return re.sub(r"[\x00-\x1f]+", " ", s).strip()



def parameters(raw, sec):
    """Параметры изделия: {имя: значение} (обозначение, наименование, материал …)."""
    out = {}
    for name in ("NeuPrtSld", "LargeText"):
        if name not in sec:
            continue
        off, ln = sec[name]
        chunk = raw[off:off + ln]
        for m in re.finditer(rb"([\x20-\xff]{3,32})\x00\xe2([\x32\x33])(.{0,60}?)\x00", chunk, re.S):
            t = re.search(r"[\w]+$", m.group(1).decode("utf-8", "replace"))
            if not t:
                continue
            key = t.group(0)
            if m.group(2)[0] == 0x33:
                try:
                    val = clean_name(m.group(3).decode("utf-8"))
                except UnicodeDecodeError:
                    continue
                if val:
                    out.setdefault(key, val)
            else:
                r = packed_at(m.group(3), 0) if m.group(3) else None
                if r:
                    out.setdefault(key, r[1])
    return out


def outline_mm(raw, sec):
    """Габарит изделия, мм."""
    for name in ("FullMData", "BasicText"):
        if name not in sec:
            continue
        off, ln = sec[name]
        chunk = raw[off:off + ln]
        m = re.search(rb"outline\x00", chunk)
        if not m:
            continue
        seg = chunk[m.end():m.end() + 12]
        vals = []
        for k in (4, 8):
            try:
                vals.append(abs(struct.unpack_from("<f", seg, k)[0]) / 1000.0)
            except Exception:
                pass
        if vals:
            return vals
    return []


def history(raw):
    """Записи истории: (ревизия, дата, пользователь, компьютер, версия)."""
    stamps = []
    for m in re.finditer(rb"\xf7\x14([\x20-\x7e\xc0-\xff]{1,24}?)\x00\xe2(.)(.)(.)(.)(.)(.)", raw, re.S):
        s, mi, h, d, mo, y = (b[0] for b in m.groups()[1:])
        try:
            dt = datetime.datetime(1900 + y, mo + 1, d, h, mi, s)
        except ValueError:
            continue
        stamps.append((m.start(), m.group(1).decode("utf-8", "replace"), dt))
    for m in re.finditer(rb"([A-Za-z0-9_.\-]{2,24})\x00\xe2(.)(.)(.)(.)(.)(.)", raw, re.S):
        s, mi, h, d, mo, y = (b[0] for b in m.groups()[1:])
        try:
            dt = datetime.datetime(1900 + y, mo + 1, d, h, mi, s)
        except ValueError:
            continue
        stamps.append((m.start(), m.group(1).decode("ascii", "replace"), dt))
    stamps.sort()
    out = []
    for t in re.finditer(rb"\xf7(.)\xe3([0-9]{1,7})\x00\x00(.{0,220}?)\x00(Creo [0-9][0-9.]*)\x00", raw, re.S):
        prev = [s for s in stamps if s[0] < t.start()]
        user = prev[-1][1] if prev else ""
        dt = prev[-1][2] if prev else None
        try:
            com = t.group(3).decode("utf-8")
        except UnicodeDecodeError:
            com = t.group(3).decode("cp1251", "replace")
        out.append((t.group(2).decode(), dt, user, clean_name(com), t.group(4).decode()))
    return out


def provenance(raw, is_part):
    """Роль изделия и родитель (заготовка / отражение / наследование)."""
    if b"MERGE_BASE_PART" in raw:
        m = re.search(rb"MERGE_BASE_PART.{0,80}?([A-Za-z0-9_\-]{5,40})\x00", raw, re.S)
        return "наследование", (m.group(1).decode("latin-1") if m else "")
    if is_part:
        for m in re.finditer(rb"ref_part_tab\x00", raw):
            nm = re.search(rb"name\x00([A-Za-z0-9_\-\.]{4,47})\x00", raw[m.end():m.end() + 200])
            if nm:
                return "производная", nm.group(1).decode("latin-1")
    return "", ""


def kind(raw):
    head = raw[:40].decode("cp1251", "replace")
    m = re.match(r"#UGC:2\s+([A-Z_/]+)", head)
    return m.group(1) if m else "?"


def scan_file(path, settings):
    raw = read_bytes(path, settings.get("max_size_mb", 0))
    if raw is None:
        return None
    sec = sections(raw)
    par = parameters(raw, sec)
    hist = history(raw)
    is_part = ".prt." in path.lower()
    role, parent = provenance(raw, is_part)
    vol = real_value(raw, "volume") or real_value(raw, "mtrl_volume")
    last = hist[-1] if hist else None
    return {
        "Файл": os.path.basename(path),
        "Тип": kind(raw),
        "Обозначение": par.get("ОБОЗНАЧЕНИЕ") or par.get("OBOZNACHENIE") or "",
        "Наименование": par.get("НАИМЕНОВАНИЕ") or par.get("NAME") or "",
        "Материал": par.get("PTC_MASTER_MATERIAL") or par.get("MATERIAL") or "",
        "Объём, мм³": ("%.0f" % vol) if vol else "",
        "Габарит, мм": ", ".join("%.1f" % v for v in outline_mm(raw, sec)),
        "Роль": role,
        "Родитель": parent,
        "Ревизия": last[0] if last else "",
        "Дата": last[1].strftime("%d.%m.%Y %H:%M") if last and last[1] else "",
        "Пользователь": last[2] if last else "",
        "Записей": len(hist),
        "Версия": last[4] if last else "",
    }


def scan_folder(folder, settings, progress=None):
    rows, paths = [], []
    if settings.get("recurse", True):
        for dp, _, files in os.walk(folder):
            for f in files:
                if MODELFILE.search(f):
                    paths.append(os.path.join(dp, f))
    else:
        for f in os.listdir(folder):
            if MODELFILE.search(f):
                paths.append(os.path.join(folder, f))
    for n, p in enumerate(sorted(paths), 1):
        if progress:
            progress(n, len(paths), p)
        try:
            r = scan_file(p, settings)
        except Exception:
            r = None
        if r:
            rows.append(r)
    return rows


def save_csv(rows, path):
    if not rows:
        return
    cols = [c for c in DEFAULT_SETTINGS["columns"] if c in rows[0]] + \
           [c for c in rows[0] if c not in DEFAULT_SETTINGS["columns"]]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter=";")
        w.writeheader()
        w.writerows(rows)


# ------------------------------------------------------------------ окно
def run_gui():
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    settings = dict(DEFAULT_SETTINGS)
    if os.path.isfile(SETTINGS_FILE):
        try:
            settings.update(json.load(open(SETTINGS_FILE, encoding="utf-8")))
        except Exception:
            pass

    root = tk.Tk()
    root.title(APP_TITLE)
    root.geometry("1200x640")

    top = ttk.Frame(root, padding=6)
    top.pack(fill="x")
    ttk.Label(top, text="Папка:").pack(side="left")
    e_folder = ttk.Entry(top, width=68)
    e_folder.insert(0, settings.get("folder", ""))
    e_folder.pack(side="left", padx=4)

    def pick():
        d = filedialog.askdirectory(initialdir=e_folder.get() or os.path.expanduser("~"))
        if d:
            e_folder.delete(0, "end")
            e_folder.insert(0, d)

    ttk.Button(top, text="Выбрать…", command=pick).pack(side="left")
    ttk.Label(top, text="Пропускать > МБ:").pack(side="left", padx=(10, 2))
    e_max = ttk.Entry(top, width=5)
    e_max.insert(0, str(settings.get("max_size_mb", 24)))
    e_max.pack(side="left")
    var_rec = tk.BooleanVar(value=settings.get("recurse", True))
    ttk.Checkbutton(top, text="с подпапками", variable=var_rec).pack(side="left", padx=8)

    mid = ttk.Frame(root, padding=(6, 0))
    mid.pack(fill="x")
    btn = ttk.Button(mid, text="Сканировать")
    btn.pack(side="left")
    ttk.Button(mid, text="Выгрузить в CSV", command=lambda: export()).pack(side="left", padx=8)
    lbl = ttk.Label(mid, text="готов")
    lbl.pack(side="left", padx=10)

    cols = [c for c in settings.get("columns", DEFAULT_SETTINGS["columns"])]
    tree = ttk.Treeview(root, columns=cols, show="headings", height=20)
    for c in cols:
        tree.heading(c, text=c)
        tree.column(c, width=200 if c == "Наименование" else 108, anchor="w")
    tree.pack(fill="both", expand=True, padx=6, pady=6)
    sb = ttk.Scrollbar(root, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")

    rows_all = []

    def worker(folder):
        def prog(i, total, path):
            lbl.config(text="%d / %d … %s" % (i, total, os.path.basename(path)[:40]))
            root.update_idletasks()
        rows = scan_folder(folder, {"max_size_mb": float(e_max.get() or 0), "recurse": var_rec.get()}, prog)
        rows_all.clear()
        rows_all.extend(rows)
        for r in rows:
            tree.insert("", "end", values=[r.get(c, "") for c in cols])
        lbl.config(text="готово: %d моделей" % len(rows))
        btn.config(state="normal")

    def go():
        folder = e_folder.get().strip()
        if not os.path.isdir(folder):
            messagebox.showwarning(APP_TITLE, "Выберите папку.")
            return
        btn.config(state="disabled")
        settings.update({"folder": folder, "max_size_mb": float(e_max.get() or 0), "recurse": var_rec.get()})
        try:
            json.dump(settings, open(SETTINGS_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        except Exception:
            pass
        threading.Thread(target=worker, args=(folder,), daemon=True).start()

    def export():
        if not rows_all:
            return
        p = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="plm_items.csv",
                                         filetypes=[("CSV", "*.csv")])
        if p:
            save_csv(rows_all, p)
            lbl.config(text="выгружено: %s" % os.path.basename(p))

    btn.config(command=go)
    root.mainloop()


def main():
    ap = argparse.ArgumentParser(description=APP_TITLE)
    ap.add_argument("--folder", help="папка для сканирования (режим без окна)")
    ap.add_argument("--csv", help="файл выгрузки (режим без окна)")
    ap.add_argument("--max-mb", type=float, default=DEFAULT_SETTINGS["max_size_mb"])
    ap.add_argument("--no-recurse", action="store_true")
    a = ap.parse_args()
    if a.folder:
        rows = scan_folder(a.folder, {"max_size_mb": a.max_mb, "recurse": not a.no_recurse})
        cols = DEFAULT_SETTINGS["columns"]
        print(" | ".join(cols))
        for r in rows:
            print(" | ".join(str(r.get(c, "")) for c in cols))
        print("\nвсего моделей: %d" % len(rows))
        if a.csv:
            save_csv(rows, a.csv)
            print("CSV: %s" % a.csv)
        return
    run_gui()


if __name__ == "__main__":
    main()

