# -*- coding: utf-8 -*-
"""harvest_gui.py — окно сканера (спека 98, tkinter, стандартная библиотека).
Дизайн: палитра Давыдовки (DESIGN_davydovka_tokens.md).
Z-корень = рука человека: чекбокс + диалог подтверждения; harvest.py — свой процесс.
"""
import json, os, subprocess, sys, time
import tkinter as tk
from tkinter import ttk, messagebox

AG = os.path.dirname(os.path.abspath(__file__))
HARVEST = os.path.join(AG, "harvest.py")
DATA = os.path.join(AG, "data")
ROOTS_DEFAULT = os.path.join(AG, "kb_roots.txt")
GUI_ROOTS = os.path.join(DATA, "harvest_gui_roots.txt")
SETTINGS = os.path.join(DATA, "harvest_settings.json")
REPORT = r"D:\AI\log\harvest\last_harvest.json"
LOGF = r"D:\AI\log\harvest\harvest.log"
LOCK = os.path.join(DATA, "harvest.lock")

# --- токены Давыдовки (DESIGN_davydovka_tokens.md) ---
BG = "#e9edf1"; CARD = "#ffffff"; BORDER = "#d6dce1"; TXT = "#171717"
MUTED = "#6d7780"; ACCENT = "#246f9e"; ACCENT_DARK = "#1d5a80"
RUN_BG = "#fff1c7"; RUN_BD = "#dfc576"
OK_BG = "#dff2df"; OK_BD = "#9fc99f"
ERR_BG = "#fde3e1"; ERR_BD = "#d9908a"
FONT = ("Arial", 10); FONT_H = ("Arial", 13, "bold"); FONT_S = ("Arial", 9)


def load_settings():
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(d):
    try:
        with open(SETTINGS, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def read_kb_roots():
    out = []
    try:
        with open(ROOTS_DEFAULT, encoding="utf-8") as f:
            for line in f:
                line = line.replace("\ufeff", "").strip()
                if line and not line.startswith("#"):
                    out.append(line)
    except Exception:
        pass
    return out


def lock_alive():
    """Живой лок с живым PID (тот же контракт, что у harvest.acquire_lock)."""
    if not os.path.exists(LOCK):
        return None
    import ctypes
    try:
        pid = int(open(LOCK, encoding="ascii", errors="ignore").read().strip() or 0)
    except Exception:
        pid = 0
    if pid and ctypes.windll.kernel32.OpenProcess(0x1000, False, pid):
        return pid
    return None


class App:
    def __init__(self, root):
        self.root = root
        root.title("ХАРВЕСТ — сканер дома (спека 98)")
        root.configure(bg=BG)
        self.sett = load_settings()
        self.checked = set(self.sett.get("roots_checked", []))
        self.z_allowed = bool(self.sett.get("z_allowed", False))
        self.pid = None
        
        # New settings
        self.var_exts = tk.StringVar(value=", ".join(self.sett.get("extensions", ["prt", "asm", "drw", "frm", "lay", "sec"])))
        self.var_markers = tk.BooleanVar(value=self.sett.get("markers", True))
        self.var_src_txt = tk.BooleanVar(value="txt" in self.sett.get("chunks_sources", ["txt", "md"]))
        self.var_src_md = tk.BooleanVar(value="md" in self.sett.get("chunks_sources", ["txt", "md"]))
        self.var_batch = tk.IntVar(value=self.sett.get("batch", 500))
        
        self._build()
        self._refresh_loop()

    def _build(self):
        head = tk.Frame(self.root, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        head.pack(fill="x", padx=16, pady=(14, 8), ipady=8)
        tk.Label(head, text="СКАНЕР ДОМА — HARVEST", bg=CARD, fg=TXT,
                 font=FONT_H).pack(anchor="w", padx=14)
        self.status = tk.Label(head, text="готов", bg=OK_BG, fg="#1f2a31",
                               highlightbackground=OK_BD, highlightthickness=1,
                               font=("Arial", 10, "bold"), padx=12, pady=4)
        self.status.pack(anchor="w", padx=14, pady=(8, 0))
        self.badge_lbl = tk.Label(head, text="", bg=RUN_BG, fg="#8a5e00",
                                 highlightbackground=RUN_BD, highlightthickness=1,
                                 font=("Arial", 9, "bold"), padx=8, pady=2)
        self.badge_lbl.pack(anchor="e", padx=14, pady=(0, 0))
        self.badge_lbl = tk.Label(head, text="", bg=RUN_BG, fg="#8a5e00",
                                 highlightbackground=RUN_BD, highlightthickness=1,
                                 font=("Arial", 9, "bold"), padx=8, pady=2)
        self.badge_lbl.pack(anchor="e", padx=14, pady=(0, 0))

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=8)

        left = tk.Frame(body, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        left.pack(side="left", fill="y", padx=(0, 8), ipady=8)
        tk.Label(left, text="КОРНИ (kb_roots.txt)", bg=CARD, fg=TXT,
                 font=("Arial", 10, "bold")).pack(anchor="w", padx=12, pady=(6, 2))
        self.root_vars = {}
        for r in read_kb_roots():
            is_z = r[:2].upper() == "Z:"
            label = r + ("   [запрещён до слова]" if is_z else "")
            v = tk.BooleanVar(value=(r in self.checked))
            cb = tk.Checkbutton(left, text=label, variable=v, bg=CARD, fg=TXT,
                                font=FONT, anchor="w", justify="left", wraplength=330)
            cb.pack(fill="x", padx=10)
            self.root_vars[r] = v

        self.var_text = tk.BooleanVar(value=bool(self.sett.get("text", False)))
        self.var_bench = tk.BooleanVar(value=bool(self.sett.get("bench", False)))
        ttk.Checkbutton(left, text="--text (факты через Ollama, медленно)",
                        variable=self.var_text).pack(anchor="w", padx=10, pady=(6, 0))
        ttk.Checkbutton(left, text="--bench (замер скорости)",
                        variable=self.var_bench).pack(anchor="w", padx=10)

        btns = tk.Frame(left, bg=CARD)
        btns.pack(fill="x", padx=10, pady=10)
        self.btn_scan = tk.Button(btns, text="СКАН", bg=ACCENT, fg="white",
                                  activebackground=ACCENT_DARK, activeforeground="white",
                                  font=("Arial", 10, "bold"), relief="flat",
                                  padx=18, pady=4, cursor="hand2", command=self.on_scan)
        self.btn_scan.pack(side="left")
        self.btn_stop = tk.Button(btns, text="СТОП", bg=CARD, fg="#8a2b23",
                                  highlightbackground=ERR_BD, font=("Arial", 10, "bold"),
                                  relief="flat", padx=14, pady=4, cursor="hand2",
                                  command=self.on_stop)
        self.btn_stop.pack(side="left", padx=8)

        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        rep = tk.Frame(right, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        rep.pack(fill="x", ipady=6)
        tk.Label(rep, text="ОТЧЁТ (last_harvest.json)", bg=CARD, fg=TXT,
                 font=("Arial", 10, "bold")).pack(anchor="w", padx=12, pady=(6, 2))
        self.report_lbl = tk.Label(rep, text="(нет отчёта)", bg=CARD, fg=TXT,
                                   font=("Courier New", 9), anchor="w", justify="left")
        self.report_lbl.pack(fill="x", padx=12)

        cols = ("root", "added", "rewrote", "deleted", "sec")
        self.tree = ttk.Treeview(rep, columns=cols, show="headings", height=7)
        for cid, txt, w in (("root", "корень", 260), ("added", "added", 70),
                            ("rewrote", "rewrote", 70), ("deleted", "deleted", 70),
                            ("sec", "сек", 70)):
            self.tree.heading(cid, text=txt)
            self.tree.column(cid, width=w, anchor="w")
        self.tree.pack(fill="x", padx=12, pady=6)

        lg = tk.Frame(right, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        lg.pack(fill="both", expand=True, pady=(8, 0), ipady=6)
        tk.Label(lg, text="ЛОГ (harvest.log, хвост 30)", bg=CARD, fg=TXT,
                 font=("Arial", 10, "bold")).pack(anchor="w", padx=12, pady=(6, 2))
        self.log_txt = tk.Text(lg, height=14, bg="#101315", fg="#c7d4dc",
                               font=("Courier New", 9), relief="flat", state="disabled")
        self.log_txt.pack(fill="both", expand=True, padx=12, pady=(0, 8))

    def _set_status(self, text, kind):
        bg, bd = {"run": (RUN_BG, RUN_BD), "ok": (OK_BG, OK_BD),
                  "err": (ERR_BG, ERR_BD)}.get(kind, (OK_BG, OK_BD))
        self.status.configure(text=text, bg=bg, highlightbackground=bd)

    def _selected_roots(self):
        sel = [r for r, v in self.root_vars.items() if v.get()]
        self.z_checked = any(r[:2].upper() == "Z:" for r in sel)
        return sel

    def on_scan(self):
        pid = lock_alive()
        if pid:
            self._set_status("уже идёт (PID %s)" % pid, "err")
            return
        roots = self._selected_roots()
        if not roots:
            self._set_status("не выбран ни один корень", "err")
            return
        allow_z = False
        if self.z_checked:
            ok = messagebox.askyesno(
                "Сетевой корень Z:",
                "Сетевой корень: медленно, территория инженера.\n"
                "Сканировать Z по слову пользователя (клик = согласие)?",
                icon="warning")
            if not ok:
                self._set_status("Z отклонён — скан не запущен", "err")
                return
            allow_z = True
            self.z_allowed = True
        try:
            os.makedirs(DATA, exist_ok=True)
            with open(GUI_ROOTS, "w", encoding="ascii", errors="ignore") as f:
                f.write("\n".join(roots))
        except Exception as e:
            self._set_status("roots-файл не записан: %s" % e, "err")
            return
        args = [sys.executable, "-u", HARVEST, "--roots", GUI_ROOTS]
        if self.var_text.get():
            args.append("--text")
        if self.var_bench.get():
            args.append("--bench")
        if allow_z:
            args.append("--allow-z")
        try:
            self.pid = subprocess.Popen(args, cwd=AG,
                                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).pid
        except Exception as e:
            self._set_status("пуск не удался: %s" % e, "err")
            return
        save_settings({"roots_checked": roots, "text": self.var_text.get(),
                       "bench": self.var_bench.get(), "z_allowed": allow_z})
        self._set_status("идёт (PID %s)" % self.pid, "run")

    def on_stop(self):
        if not messagebox.askyesno("СТОП", "Прервать текущий скан?"):
            return
        import importlib, harvest
        importlib.reload(harvest)
        res = harvest.stop()
        if res.get("stopped"):
            self._set_status("остановлен (PID %s)" % res.get("pid"), "ok")
        else:
            self._set_status("СТОП: %s" % res.get("reason"), "err")

    def _refresh_loop(self):
        pid = lock_alive()
        if pid and self.status.cget("text").startswith(("готов", "остановлен", "СТОП")):
            self._set_status("идёт (PID %s)" % pid, "run")
        elif not pid and self.status.cget("text").startswith("идёт"):
            self._set_status("готово", "ok")
        # отчёт
        try:
            with open(REPORT, encoding="utf-8") as f:
                d = json.load(f)
            files = (d.get("tables") or {}).get("models_raw", "?")
            ah = ", ".join(d.get("added_head", [])[:6])
            self.report_lbl.configure(text=(
                "ts: %s\nseconds: %s | файлов: %s | added_head: %s…\n"
                "deleted: %s | rewritten: %s | vanished_guard: %s" % (
                    d.get("ts"), d.get("seconds"), files, ah,
                    d.get("deleted"), d.get("rewritten"), d.get("vanished_guard"))))
            for i in self.tree.get_children():
                self.tree.delete(i)
            for root, pr in (d.get("per_root") or {}).items():
                self.tree.insert("", "end", values=(
                    root, pr.get("added"), pr.get("rewrote"),
                    pr.get("deleted"), pr.get("seconds")))
        except Exception:
            pass
        # лог: хвост 30
        try:
            with open(LOGF, encoding="utf-8", errors="ignore") as f:
                tail = f.read().splitlines()[-30:]
            self.log_txt.configure(state="normal")
            self.log_txt.delete("1.0", "end")
            self.log_txt.insert("1.0", "\n".join(tail))
            self.log_txt.see("end")
            self.log_txt.configure(state="disabled")
        except Exception:
            pass
        self.root.after(5000, self._refresh_loop)


def main():
    root = tk.Tk()
    root.geometry("980x640")
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
