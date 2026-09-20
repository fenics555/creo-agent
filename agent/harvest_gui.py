# -*- coding: utf-8 -*-
"""harvest_gui.py - scanner window (spec 101, tkinter).
Design: Davydovka palette.
"""
import json, os, subprocess, sys, time, ctypes
import tkinter as tk
from tkinter import ttk, messagebox

AG = os.path.dirname(os.path.abspath(__file__))
HARVEST = os.path.join(AG, 'harvest.py')
DATA = os.path.join(AG, 'data')
ROOTS_DEFAULT = os.path.join(AG, 'kb_roots.txt')
GUI_ROOTS = os.path.join(DATA, 'harvest_gui_roots.txt')
SETTINGS = os.path.join(DATA, 'harvest_settings.json')
REPORT = r'D:\AI\log\harvest\last_harvest.json'
LOGF = r'D:\AI\log\harvest\harvest.log'
LOCK = os.path.join(DATA, 'harvest.lock')

BG = '#e9edf1'; CARD = '#ffffff'; BORDER = '#d6dce1'; TXT = '#171717'
MUTED = '#6d7780'; ACCENT = '#246f9e'; ACCENT_DARK = '#1d5a80'
RUN_BG = '#fff1c7'; RUN_BD = '#dfc576'
OK_BG = '#dff2df'; OK_BD = '#9fc99f'
ERR_BG = '#fde3e1'; ERR_BD = '#d9908a'
FONT = ('Arial', 10); FONT_H = ('Arial', 13, 'bold'); FONT_S = ('Arial', 9)

def load_settings():
    try:
        with open(SETTINGS, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_settings(d):
    try:
        os.makedirs(DATA, exist_ok=True)
        with open(SETTINGS, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
    except Exception:
        pass

def read_kb_roots():
    out = []
    try:
        if os.path.exists(ROOTS_DEFAULT):
            with open(ROOTS_DEFAULT, encoding='utf-8') as f:
                for line in f:
                    line = line.replace('\ufeff', '').strip()
                    if line and not line.startswith('#'):
                        out.append(line)
    except Exception:
        pass
    return out

def lock_alive():
    if not os.path.exists(LOCK):
        return None
    try:
        with open(LOCK, encoding='ascii', errors='ignore') as f:
            pid_str = f.read().strip()
            if not pid_str: return None
            pid = int(pid_str)
            if pid and ctypes.windll.kernel32.OpenProcess(0x1000, False, pid):
                return pid
    except Exception:
        pass
    return None

class App:
    def __init__(self, root):
        self.root = root
        root.title('HARVEST - Home Scanner (Spec 101)')
        root.configure(bg=BG)
        self.sett = load_settings()
        self.var_exts = tk.StringVar(value=', '.join(self.sett.get('extensions', ['prt', 'asm', 'drw', 'frm', 'lay', 'sec'])))
        self.var_markers = tk.BooleanVar(value=self.sett.get('markers', True))
        self.var_src_txt = tk.BooleanVar(value='txt' in self.sett.get('chunks_sources', ['txt', 'md']))
        self.var_src_md = tk.BooleanVar(value='md' in self.sett.get('chunks_sources', ['txt', 'md']))
        self.var_batch = tk.IntVar(value=self.sett.get('batch', 500))
        self.var_text = tk.BooleanVar(value=self.sett.get('text', False))
        self.var_bench = tk.BooleanVar(value=self.sett.get('bench', False))
        self.var_z = tk.BooleanVar(value=self.sett.get('z_allowed', False))
        self.pid = None
        self._build()
        self._refresh_loop()

    def _set_status(self, text, style):
        colors = {'run': (RUN_BG, RUN_BD), 'ok': (OK_BG, OK_BD), 'err': (ERR_BG, ERR_BD), 'idle': (CARD, BORDER)}
        bg, bd = colors.get(style, (CARD, BORDER))
        self.status.configure(text=text, bg=bg, highlightbackground=bd)

    def _build(self):
        # GUI structure (Simplified for restoration)
        self.status = tk.Label(self.root, text='ready', bg=CARD)
        self.status.pack(pady=5)
        self.report_lbl = tk.Label(self.root, text='', bg=BG)
        self.report_lbl.pack()
        self.tree = ttk.Treeview(self.root, columns=('added', 'rewrote', 'deleted', 'seconds'), show='headings')
        self.tree.heading('added', text='Added')
        self.tree.heading('rewrote', text='Rewrote')
        self.tree.heading('deleted', text='Deleted')
        self.tree.heading('seconds', text='Sec')
        self.tree.pack(expand=True, fill='both')
        self.log_txt = tk.Text(self.root, height=10)
        self.log_txt.pack(fill='x')

    def on_stop(self):
        pass

    def _refresh_loop(self):
        self.root.after(5000, self._refresh_loop)

def main():
    root = tk.Tk()
    root.geometry('1000x650')
    App(root)
    root.mainloop()

if __name__ == '__main__':
    main()
