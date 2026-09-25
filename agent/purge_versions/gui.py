import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
from pathlib import Path
from datetime import datetime
import time
import sys

# движок лежит рядом с окном (программа автономна)
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from purge_versions import preview, execute, Lock
except ImportError:
    # Fallback for testing if path is wrong
    class Lock:
        def __init__(self, p): self.p = Path(p)
        def acq(self): return True, None
        def rel(self): pass
    def preview(root, keep, creo_mode): return {"groups": [], "singles": []}
    def execute(root, keep, creo_mode, backup_dir): return {}

SETTINGS_FILE = Path(__file__).resolve().parent / "gui_settings.json"
LOG_FILE = Path(r"D:\AI\log\purge_versions\purge.log")
LAST_PURGE_FILE = Path(r"D:\AI\log\purge_versions\last_purge.json")
LOCK_FILE = Path(r"D:\AI\log\purge_versions\purge.lock")

class PurgeGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("V1 — ОКНО ЧИСТИЛЬЩИКА")
        self.root.geometry("850x650")
        self.root.configure(bg="#e9edf1")
        
        self.settings = self.load_settings()
        self.current_plan = None
        
        self.setup_ui()
        self.refresh_info_panel()

    def load_settings(self):
        if SETTINGS_FILE.exists():
            try:
                return json.loads(SETTINGS_FILE.read_text(encoding='utf-8'))
            except: pass
        return {"root": "", "keep": 1, "creo_mode": False, "backup_dir": "", "history": []}

    def save_settings(self):
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(self.settings, ensure_ascii=False, indent=2), encoding='utf-8')

    def setup_ui(self):
        # Toolbar / Settings
        toolbar = tk.Frame(self.root, bg="#ffffff", bd=1, relief="solid", padx=10, pady=10)
        toolbar.pack(fill="x", padx=10, pady=10)

        tk.Label(toolbar, text="Корень:", bg="#ffffff").grid(row=0, column=0, sticky="w")
        self.root_var = tk.StringVar(value=self.settings.get("root", ""))
        self.root_combo = ttk.Combobox(toolbar, textvariable=self.root_var, width=50)
        self.root_combo['values'] = self.settings.get("history", [])
        self.root_combo.grid(row=0, column=1, padx=5, pady=5)
        self.root_combo.bind("<<ComboboxSelected>>", self.on_setting_changed)
        
        tk.Button(toolbar, text="Обзор", command=self.browse_root).grid(row=0, column=2, padx=5)

        tk.Label(toolbar, text="Keep:", bg="#ffffff").grid(row=1, column=0, sticky="w")
        self.keep_var = tk.IntVar(value=self.settings.get("keep", 1))
        self.keep_spin = tk.Spinbox(toolbar, from_=1, to=100, textvariable=self.keep_var, width=5)
        self.keep_spin.grid(row=1, column=1, sticky="w", padx=5)
        self.keep_spin.bind("<ButtonRelease-1>", self.on_setting_changed)

        self.creo_var = tk.BooleanVar(value=self.settings.get("creo_mode", False))
        tk.Checkbutton(toolbar, text="Creo-mode", variable=self.creo_var, bg="#ffffff", command=self.on_setting_changed).grid(row=1, column=1, sticky="e", padx=(50, 0))

        tk.Label(toolbar, text="Backup Dir:", bg="#ffffff").grid(row=2, column=0, sticky="w")
        self.backup_var = tk.StringVar(value=self.settings.get("backup_dir", ""))
        self.backup_entry = tk.Entry(toolbar, textvariable=self.backup_var, width=50)
        self.backup_entry.grid(row=2, column=1, padx=5, pady=5)
        self.backup_entry.bind("<FocusOut>", self.on_setting_changed)

        btn_frame = tk.Frame(toolbar, bg="#ffffff")
        btn_frame.grid(row=3, column=0, columnspan=3, pady=10)
        self.btn_plan = tk.Button(btn_frame, text="ПЛАН", width=15, command=self.run_preview)
        self.btn_plan.pack(side="left", padx=5)
        self.btn_execute = tk.Button(btn_frame, text="ЧИСТИТЬ", width=15, state="disabled", command=self.confirm_execute)
        self.btn_execute.pack(side="left", padx=5)
        self.btn_readme = tk.Button(btn_frame, text="README", width=15, command=self.show_readme)
        self.btn_readme.pack(side="left", padx=5)

        self.warn_label = tk.Label(self.root, text="", bg="#fff1c7", fg="#856404", font=("Arial", 10, "bold"))
        self.warn_label.pack(fill="x", padx=10)

        self.tree_frame = tk.Frame(self.root, bg="#e9edf1")
        self.tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.tree = ttk.Treeview(self.tree_frame, columns=("group", "members", "target"), show="headings")
        for col, head in zip(("group", "members", "target"), ("Группа", "Версии", "Уйдёт")):
            self.tree.heading(col, text=head)
            self.tree.column(col, width=200)
        self.tree.pack(fill="both", expand=True)

        self.info_panel = tk.LabelFrame(self.root, text="ИНФО", bg="#ffffff", padx=10, pady=10)
        self.info_panel.pack(fill="x", padx=10, pady=10)
        self.info_text = tk.Text(self.info_panel, height=6, width=80, state="disabled", font=("Consolas", 9), bg="#f8f9fa")
        self.info_text.pack(fill="x")


    def on_setting_changed(self, event=None):
        self.settings.update({"root": self.root_var.get(), "keep": self.keep_var.get(), "creo_mode": self.creo_var.get(), "backup_dir": self.backup_var.get()})
        root = self.root_var.get()
        if root and root not in self.settings.get("history", []):
            h = self.settings.get("history", [])
            h.append(root)
            self.settings["history"] = h[-10:]
            self.root_combo['values'] = self.settings["history"]
        self.save_settings()
        self.btn_execute.config(state="disabled")
        self.warn_label.config(text="⚠️ сетевой корень, медленно, территория инженера" if root.startswith("\\\\") or "Z:\\" in root else "")

    def browse_root(self):
        p = filedialog.askdirectory()
        if p: self.root_var.set(p); self.on_setting_changed()

    def run_preview(self):
        root = self.root_var.get()
        if not root: return messagebox.showwarning("Внимание", "Выберите корень!")
        lock = Lock(LOCK_FILE)
        ok, err = lock.acq()
        if not ok: return self.show_error(err)
        try:
            for i in self.tree.get_children(): self.tree.delete(i)
            self.current_plan = preview(Path(root), self.keep_var.get(), self.creo_var.get())
            for g in self.current_plan.get("groups", []): self.tree.insert("", "end", values=(g["base"], ", ".join(g["members"]), g.get("target", "")))
            for s in self.current_plan.get("singles", []): self.tree.insert("", "end", values=("---", s, "---"))
            self.btn_execute.config(state="normal")
        except Exception as e: messagebox.showerror("Ошибка", str(e))
        finally: lock.rel()

    def show_error(self, err):
        self.info_text.config(state="normal"); self.info_text.delete("1.0", tk.END); self.info_text.insert(tk.END, f"!!! {err}"); self.info_text.config(state="disabled")

    def confirm_execute(self):
        bd = self.backup_var.get() or (Path(self.root_var.get()) / "_purge_backup" / datetime.datetime.now().strftime("%Y%m%d"))
        if messagebox.askyesno("Подтверждение", f"Начать очистку в:\n{bd}?"):
            lock = Lock(LOCK_FILE)
            if not lock.acq()[0]: return messagebox.showerror("Ошибка", "Уже запущено")
            _t0 = time.time()
            try:
                rep = execute(Path(self.root_var.get()), self.keep_var.get(), self.creo_var.get(), Path(bd))
                self.refresh_info_panel()
                messagebox.showinfo("Готово", "Очистка завершена. (за %.1f с)" % (time.time() - _t0))
                self.btn_execute.config(state="disabled")
            except Exception as e: messagebox.showerror("Ошибка", str(e))
            finally: lock.rel()

    def refresh_info_panel(self):
        self.info_text.config(state="normal"); self.info_text.delete("1.0", tk.END)
        if LAST_PURGE_FILE.exists():
            try:
                d = json.loads(LAST_PURGE_FILE.read_text(encoding='utf-8'))
                m = datetime.datetime.fromtimestamp(LAST_PURGE_FILE.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                self.info_text.insert(tk.END, f"--- ПОСЛЕДНИЙ ПРОГОН ({d.get('root', 'unknown')}) ---\n")
                self.info_text.insert(tk.END, f"Время: {m} | Было: {d.get('было_версий', 0)} | Перенесено: {len(d.get('перенесено_парами', []))} | Освобождено: {d.get('освобождено_байт', 0)//1024} KB\n")
            except: self.info_text.insert(tk.END, "Ошибка чтения last_purge.json\n")
        else: self.info_text.insert(tk.END, "Нет данных.\n")
        self.info_text.insert(tk.END, "\n--- LOG ---\n")
        if LOG_FILE.exists():
            try:
                for l in LOG_FILE.read_text(encoding='utf-8', errors='replace').splitlines()[-10:]: self.info_text.insert(tk.END, f"{l}\n")
            except: pass
    def show_readme(self):
        p = Path(__file__).resolve().parent / "README.md"
        try:
            text = p.read_text(encoding="utf-8")
        except Exception as e:
            self.show_error("README не прочитан: %s" % e)
            return
        w = tk.Toplevel(self.root)
        w.title("README — Очистка версий Creo")
        w.geometry("900x600")
        txt = tk.Text(w, font=("Consolas", 10), padx=8, pady=8)
        sb = ttk.Scrollbar(w, command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        txt.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        txt.insert("1.0", text)
        txt.config(state="disabled")

        self.info_text.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk()
    app = PurgeGUI(root)
    root.mainloop()

