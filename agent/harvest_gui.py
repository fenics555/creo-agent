# -*- coding: utf-8 -*-
\"\"\"harvest_gui.py - scanner window (spec 101, tkinter).
Design: Davydovka palette.
\"\"\"
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
        top = tk.Frame(self.root, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        top.pack(fill='x', padx=16, pady=(14, 8), ipady=4)
        tk.Label(top, text='HOME SCANNER', bg=CARD, font=FONT_H).pack(side='left', padx=10)
        self.status = tk.Label(top, text='ready', bg=CARD, font=FONT_S, padx=10)
        self.status.pack(side='right', padx=10)
        main_frame = tk.Frame(self.root, bg=BG)
        main_frame.pack(fill='both', expand=True, padx=16, pady=8)
        set_frame = tk.LabelFrame(main_frame, text='SETTINGS', bg=CARD, font=FONT_S, padx=10, pady=10)
        set_frame.pack(side='left', fill='y', padx=(0, 8))
        tk.Label(set_frame, text='Extensions:', bg=CARD, font=FONT_S).pack(anchor='w')
        tk.Entry(set_frame, textvariable=self.var_exts, width=20).pack(fill='x', pady=(0, 10))
        tk.Checkbutton(set_frame, text='Markers', variable=self.var_markers, bg=CARD, font=FONT_S).pack(anchor='w')
        tk.Label(set_frame, text='Sources:', bg=CARD, font=FONT_S).pack(anchor='w', pady=(5, 0))
        tk.Checkbutton(set_frame, text='.txt', variable=self.var_src_txt, bg=CARD, font=FONT_S).pack(anchor='w')
        tk.Checkbutton(set_frame, text='.md', variable=self.var_src_md, bg=CARD, font=FONT_S).pack(anchor='w')
        tk.Label(set_frame, text='Batch:', bg=CARD, font=FONT_S).pack(anchor='w', pady=(10, 0))
        tk.Spinbox(set_frame, from_=1, to=10000, textvariable=self.var_batch, width=18).pack(fill='x')
        tk.Label(set_frame, text='Options:', bg=CARD, font=FONT_S).pack(anchor='w', pady=(10, 0))
        tk.Checkbutton(set_frame, text='Text', variable=self.var_text, bg=CARD, font=FONT_S).pack(anchor='w')
        tk.Checkbutton(set_frame, text='Bench', variable=self.var_bench, bg=CARD, font=FONT_S).pack(anchor='w')
        tk.Checkbutton(set_frame, text='Allow Z:', variable=self.var_z, bg=CARD, font=FONT_S).pack(anchor='w')
        tk.Button(set_frame, text='START', command=self.on_scan, bg=ACCENT, fg='white', font=FONT_S, height=2).pack(fill='x', pady=(20, 0))
        tk.Button(set_frame, text='STOP', command=self.on_stop, bg=ERR_BG, fg=TXT, font=FONT_S).pack(fill='x', pady=(5, 0))

    def on_scan(self):
        roots = read_kb_roots()
        if not roots:
            messagebox.showerror('Error', 'Roots not found!')
            return
        exts_list = [e.strip() for e in self.var_exts.get().split(',') if e.strip()]
        srcs = []
        if self.var_src_txt.get(): srcs.append('txt')
        if self.var_src_md.get(): srcs.append('md')
        new_sett = {
            'extensions': exts_list, 'markers': self.var_markers.get(),
            'chunks_sources': srcs, 'batch': self.var_batch.get(),
            'text': self.var_text.get(), 'bench': self.var_bench.get(),
            'z_allowed': self.var_z.get(), 'roots_checked': roots
        }
        save_settings(new_sett)
        os.makedirs(DATA, exist_ok=True)
        with open(GUI_ROOTS, 'w', encoding='utf-8') as f:
            f.write('\\n'.join(roots))
        args = [sys.executable, '-u', HARVEST, '--roots', GUI_ROOTS]
        if self.var_text.get(): args.append('--text')
        if self.var_bench.get(): args.append('--bench')
        if self.var_z.get(): args.append('--allow-z')
        try:
            self.pid = subprocess.Popen(args, cwd=AG, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).pid
            self._set_status(f'running (PID {self.pid})', 'run')
        except Exception as e:
            self._set_status(f'Error: {e}', 'err')

    def on_stop(self):
        if not messagebox.askyesno('STOP', 'Stop current scan?'):
            return
        try:
            import importlib, harvest
            importlib.reload(harvest)
            res = harvest.stop()
            if res.get('stopped'):
                self._set_status('stopped', 'ok')
            else:
                self._set_status(f'STOP: {res.get(\'reason\')}', 'err')
        except Exception as e:
            self._set_status(f'Stop error: {e}', 'err')

    def _refresh_loop(self):
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
                self.report_lbl.configure(text=f'ts: {ts} | sec: {sec} | files: {files} | added: {d.get(\'added\',0)}')
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
                self.log_txt.insert('1.0', '\\n'.join(tail))
                self.log_txt.see('end')
                self.log_txt.configure(state='disabled')
        except Exception: pass
        self.root.after(5000, self._refresh_loop)

def main():
    root = tk.Tk()
    root.geometry('1000x650')
    App(root)
    root.mainloop()

if __name__ == '__main__':
    main()

