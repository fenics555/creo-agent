# -*- coding: utf-8 -*-
"""
harvest_gui_panels.py - Mixin for harvest_gui.py
Contains UI panels (info, log, badge) and handlers.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import json, os, subprocess, sys, time, ctypes

class AppPanelsMixin:
    def _set_status(self, text, style):
        from harvest_gui import BG, CARD, BORDER, RUN_BG, RUN_BD, OK_BG, OK_BD, ERR_BG, ERR_BD
        colors = {'run': (RUN_BG, RUN_BD), 'ok': (OK_BG, OK_BD), 'err': (ERR_BG, ERR_BD), 'idle': (CARD, BORDER)}
        bg, bd = colors.get(style, (CARD, BORDER))
        self.status.configure(text=text, bg=bg, highlightbackground=bd)

    def _build_info_panel(self):
        from harvest_gui import BG, CARD, BORDER, TXT
        # Status bar
        self.status = tk.Label(self.root, text='ready', bg=CARD, relief='flat', bd=1)
        self.status.pack(fill='x', padx=5, pady=2)

        # Report label
        self.report_lbl = tk.Label(self.root, text='', bg=BG, font=('Arial', 9))
        self.report_lbl.pack(pady=2)

        # Treeview for results
        self.tree = ttk.Treeview(self.root, columns=('added', 'rewrote', 'deleted', 'seconds'), show='headings')
        self.tree.heading('added', text='Added')
        self.tree.heading('rewrote', text='Rewrote')
        self.tree.heading('deleted', text='Deleted')
        self.tree.heading('seconds', text='Sec')
        self.tree.column('added', width=80, anchor='center')
        self.tree.column('rewrote', width=80, anchor='center')
        self.tree.column('deleted', width=80, anchor='center')
        self.tree.column('seconds', width=60, anchor='center')
        self.tree.pack(expand=True, fill='both', padx=5, pady=5)

        # Log text area
        self.log_txt = tk.Text(self.root, height=8, font=('Consolas', 9))
        self.log_txt.pack(fill='x', padx=5, pady=5)

    def on_stop(self):
        from harvest_gui import messagebox
        if not messagebox.askyesno('STOP', 'Stop current scan?'):
            return
        try:
            import importlib, harvest
            importlib.reload(harvest)
            res = harvest.stop()
            if res.get('stopped'):
                self._set_status('stopped', 'ok')
            else:
                self._set_status(f"STOP: {res.get('reason')}", 'err')
        except Exception as e:
            self._set_status(f'Stop error: {e}', 'err')

    def _refresh_loop(self):
        from harvest_gui import LOCK, REPORT, LOGF, lock_alive
        pid = lock_alive()
        if pid:
            if self.status.cget('text').startswith(('ready', 'stopped', 'STOP')):
                self._set_status(f'running (PID {pid})', 'run')
        else:
            if self.status.cget('text').startswith('running'):
                self._set_status('ready', 'ok')
        
        try:
            if os.path.exists(REPORT):
                with open(REPORT, encoding='utf-8') as f:
                    d = json.load(f)
                files = (d.get('tables') or {}).get('models_raw', '0')
                ts = d.get('ts', '-')
                sec = d.get('seconds', '0')
                self.report_lbl.configure(text=f'ts: {ts} | sec: {sec} | files: {files} | added: {d.get("added", 0)}')
                for i in self.tree.get_children(): self.tree.delete(i)
                for r, p in (d.get('per_root') or {}).items():
                    self.tree.insert('', 'end', values=(r, p.get('added'), p.get('rewrote'), p.get('deleted'), p.get('seconds')))
        except Exception: pass
        
        try:
            if os.path.exists(LOGF):
                with open(LOGF, encoding='utf-8', errors='ignore') as f:
                    tail = f.read().splitlines()[-30:]
                self.log_txt.configure(state='normal')
                self.log_txt.delete('1.0', 'end')
                self.log_txt.insert('1.0', '\n'.join(tail))
                self.log_txt.see('end')
                self.log_txt.configure(state='disabled')
        except Exception: pass
        
        self.root.after(5000, self._refresh_loop)
