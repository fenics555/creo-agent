import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import json
import threading
import os
import sys
import datetime
from pathlib import Path

# Import agent environment
sys.path.append(r'D:\AI\tools\agent')
try:
    import pdf_refresh_batch as batch_tool
    import creo_ops_tools as CT
except ImportError:
    batch_tool = None
    CT = None

# Design Tokens
BG_MAIN = "#e9edf1"
BG_PANEL = "#ffffff"
BG_PANEL_ALT = "#d6dce1"
BORDER_PANEL = "#d6dce1"
TEXT_MAIN = "#171717"
TEXT_SECONDARY = "#6d7780"
STATUS_WORKING_BG = "#fff1c7"
STATUS_DONE_BG = "#dff2df"
STATUS_ERROR_BG = "#fde3e1"
ACCENT_BLUE = "#246f9e"

SETTINGS_PATH = Path(r'D:\AI\tools\agent\data\pdf_refresh_settings.json')
DB_PATH = Path(r'D:\AI\tools\agent\data\harvest.db')
REPORT_PATH = Path(r'D:\AI\log\pdfrefresh\last_refresh.json')
LOG_DIR = Path(r'D:\AI\log\pdfrefresh')

class PDFRefreshGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Refresh Batch")
        self.root.geometry("1100x750")
        self.root.configure(bg=BG_MAIN)
        self.settings = self.load_settings()
        self.is_running = False
        self.selected_items = []
        self._setup_ui()
        self._load_data()
        self._load_report()

    def load_settings(self):
        if SETTINGS_PATH.exists():
            try:
                with open(SETTINGS_PATH, 'r', encoding='utf-8') as f: return json.load(f)
            except: pass
        return {"root": "D:/AI/tools/agent/data", "limit": 20, "auto_select_outdated": True}

    def save_settings(self):
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_PATH, 'w', encoding='utf-8') as f: json.dump(self.settings, f, indent=4)

    def _setup_ui(self):
        main_frame = tk.Frame(self.root, bg=BG_MAIN)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)
        top_frame = tk.Frame(main_frame, bg=BG_PANEL, relief=tk.SOLID, borderwidth=1)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Label(top_frame, text="Настройки", bg=BG_PANEL, font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=10, pady=5)
        self.root_entry = tk.Entry(top_frame, width=40)
        self.root_entry.insert(0, self.settings.get("root", ""))
        self.root_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="Обзор", command=self._browse_root).pack(side=tk.LEFT, padx=5)
        self.limit_var = tk.IntVar(value=self.settings.get("limit", 20))
        tk.Label(top_frame, text="Лимит:", bg=BG_PANEL).pack(side=tk.LEFT, padx=5)
        tk.Entry(top_frame, textvariable=self.limit_var, width=5).pack(side=tk.LEFT, padx=5)
        self.auto_select_var = tk.BooleanVar(value=self.settings.get("auto_select_outdated", True))
        tk.Checkbutton(top_frame, text="Авто-выбор", variable=self.auto_select_var, bg=BG_PANEL).pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="Применить", command=self._apply_settings, bg=ACCENT_BLUE, fg="white").pack(side=tk.RIGHT, padx=10)
        table_frame = tk.Frame(main_frame, bg=BG_PANEL, relief=tk.SOLID, borderwidth=1)
        table_frame.pack(fill=tk.BOTH, expand=True)
        cols = ("select", "model", "pdf", "status", "dir")
        self.tree = ttk.Treeview(table_frame, columns=cols, show='headings', selectmode='none')
        for c in cols: self.tree.heading(c, text=c)
        self.tree.column("select", width=30, anchor="center")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<Button-1>", self._on_tree_click)
        bottom_frame = tk.Frame(main_frame, bg=BG_MAIN)
        bottom_frame.pack(fill=tk.X, pady=(10, 0))
        self.btn_plan = tk.Button(bottom_frame, text="ПЛАН", command=self._run_plan, width=15, height=2)
        self.btn_plan.pack(side=tk.LEFT, padx=5)
        self.btn_exec = tk.Button(bottom_frame, text="ПЕРЕПЕЧАТЬ", command=self._confirm_execute, state=tk.DISABLED, width=15, height=2)
        self.btn_exec.pack(side=tk.LEFT, padx=5)
        info_frame = tk.Frame(main_frame, bg=BG_MAIN)
        info_frame.pack(fill=tk.X, pady=(10, 0))
        self.report_label = tk.Label(info_frame, text="Отчёт: нет данных", bg=BG_PANEL, relief=tk.SOLID, borderwidth=1, anchor="nw", justify=tk.LEFT, padx=5, pady=5)
        self.report_label.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        self.log_text = tk.Text(info_frame, height=6, width=50, bg="#f0f0f0", font=("Consolas", 9))
        self.log_text.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.status_bar = tk.Label(self.root, text="Готово", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _load_data(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        self.selected_items = []
        try:
            conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row; cur = conn.cursor()
            q_db = DB_PATH
            if os.path.isdir(self.settings["root"]): q_db = os.path.join(self.settings["root"], 'data', 'harvest.db')
            cur.execute("SELECT model, pdf_path, freshness FROM pairs"); rows = cur.fetchall(); conn.close()
            for r in rows:
                st, tags = r['freshness'], ()
                if st == "актуален": tags = ("done",)
                elif st == "устарел": tags = ("working",)
                iid = self.tree.insert("", tk.END, values=("☐", r['model'], r['pdf_path'], st, os.path.dirname(r['model'])), tags=tags)
                if self.settings["auto_select_outdated"] and st == "устарел":
                    self.selected_items.append(iid); self.tree.item(iid, values=(("☑",) + r['model'], r['pdf_path'], st, os.path.dirname(r['model'])))
            self.tree.tag_configure("working", background=STATUS_WORKING_BG)
            self.tree.tag_configure("done", background=STATUS_DONE_BG)
            self._update_buttons()
        except Exception as e: self.report_label.config(text=f"Ошибка: {e}")

    def _load_report(self):
        if REPORT_PATH.exists():
            try:
                with open(REPORT_PATH, 'r', encoding='utf-8') as f: d = json.load(f)
                self.report_label.config(text=f"ОТЧЁТ ({d['timestamp']})\nБыло: {d['was_outdated']}\nСтало: {d['became_actual']}\nОшибок: {len(d['errors'])}")
            except: pass

    def _browse_root(self):
        p = filedialog.askdirectory()
        if p: self.root_entry.delete(0, tk.END); self.root_entry.insert(0, p)

    def _apply_settings(self):
        self.settings.update({"root": self.root_entry.get(), "limit": self.limit_var.get(), "auto_select_outdated": self.auto_select_var.get()})
        self.save_settings(); self._load_data(); messagebox.showinfo("Инфо", "Применено")
    def _on_tree_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item: return
        if self.tree.identify_column(event.x) == "#1":
            if item in self.selected_items: self.selected_items.remove(item); self.tree.item(item, values=(("☐",) + self.tree.item(item)["values"][1:]))
            else: self.selected_items.append(item); self.tree.item(item, values=(("☑",) + self.tree.item(item)["values"][1:]))
        else:
            if item in self.selected_items: self.selected_items.remove(item); self.tree.item(item, values=(("☐",) + self.tree.item(item)["values"][1:]))
            else: self.selected_items.append(item); self.tree.item(item, values=(("☑",) + self.tree.item(item)["values"][1:]))
        self._update_buttons()

    def _update_buttons(self):
        self.btn_exec.config(state=tk.NORMAL if self.selected_items else tk.DISABLED)

    def _run_plan(self):
        self.status_bar.config(text="Формирование плана...", bg=STATUS_WORKING_BG)
        def t(): self.root.after(0, self._show_plan); threading.Thread(target=lambda: None, daemon=True).start()
        t()

    def _show_plan(self):
        pw = tk.Toplevel(self.root); pw.title("План перепечатки"); pw.geometry("400x200")
        tk.Label(pw, text=f"Будет перепечатано:\n{len(self.selected_items)} чертежей", font=("Arial", 12)).pack(pady=20)
        tk.Button(pw, text="OK", command=pw.destroy).pack()
        self.btn_exec.config(state=tk.NORMAL); self.status_bar.config(text="Готово", bg="systemButtonFace")

    def _confirm_execute(self):
        msg = f"Будет перепечатано {len(self.selected_items)} чертежей.\nЭкспорт будет выполнен рядом с чертежами.\n\nПродолжить?"
        if messagebox.askyesno("Подтверждение", msg): self._execute_batch()

    def _execute_batch(self):
        if self.is_running: return
        self.is_running = True; self.btn_exec.config(state=tk.DISABLED); self.btn_plan.config(state=tk.DISABLED)
        self.status_bar.config(text="ПЕРЕПЕЧАТЬ ИДЁТ...", bg=STATUS_WORKING_BG)
        threading.Thread(target=self._batch_thread, daemon=True).start()

    def _batch_thread(self):
        try:
            class Args: pass
            a = Args(); a.execute=True; a.dry_run=False; a.root=self.settings['root']; a.limit=self.settings['limit']; a.report=False
            batch_tool.run_batch(a)
            self.root.after(0, self._on_batch_done)
        except Exception as e: self.root.after(0, lambda: self._on_batch_error(str(e)))

    def _on_batch_done(self):
        self.is_running = False; self.btn_exec.config(state=tk.NORMAL); self.btn_plan.config(state=tk.NORMAL)
        self.status_bar.config(text="ГОТОВО", bg=STATUS_DONE_BG); self._load_data(); self._load_report()

    def _on_batch_error(self, e):
        self.is_running = False; self.btn_exec.config(state=tk.NORMAL); self.btn_plan.config(state=tk.NORMAL)
        self.status_bar.config(text="ОШИБКА", bg=STATUS_ERROR_BG); messagebox.showerror("Ошибка", e)

if __name__ == "__main__":
    r = tk.Tk(); app = PDFRefreshGUI(r); r.mainloop()
