# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import subprocess
import sys
import time
import ctypes
from harvest_gui_panels import AppPanelsMixin

# Constants
BG = '#ffffff'
CARD = '#f0f0f0'
BORDER = '#cccccc'
RUN_BG = '#ffcccc'
RUN_BD = 1
OK_BG = '#ccffcc'
OK_BD = 1
ERR_BG = '#ffcccc'
ERR_BD = 1
TXT = '#000000'
LOCK = os.path.join('data', 'harvest.lock')
REPORT = os.path.join('data', 'harvest_settings.json')
LOGF = os.path.join('data', 'harvest.log')

def lock_alive():
    if not os.path.exists(LOCK):
        return None
    try:
        with open(LOCK, 'r', encoding='utf-8') as f:
            pid_str = f.read().strip()
            if not pid_str:
                return None
            pid = int(pid_str)
            # Check if process is running on Windows
            import ctypes
            kernel32 = ctypes.windll.kernel32
            PROCESS_QUERY_INFORMATION = 0x0400
            handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                return pid
    except Exception:
        pass
    return None

class HarvestGUI(AppPanelsMixin):
    def __init__(self, root):
        self.root = root
        self.root.title('Harvest GUI')
        self.root.geometry('600x500')
        self.root.configure(bg=BG)
        self._build_info_panel()
        self._setup_controls()
        self._refresh_loop()

    def _setup_controls(self):
        ctrl_frame = tk.Frame(self.root, bg=BG)
        ctrl_frame.pack(fill='x', padx=5, pady=5)
        
        self.stop_btn = tk.Button(ctrl_frame, text='STOP', command=self.on_stop, bg='#ff4444', fg='white')
        self.stop_btn.pack(side='right')

        self.badge_lbl = tk.Label(ctrl_frame, text='', bg=CARD, relief='sunken')
        self.badge_lbl.pack(side='left', padx=5)

    def update_badge(self, text):
        self.badge_lbl.configure(text=text)

    def _refresh_loop(self):
        # Call parent refresh
        super()._refresh_loop()
        
        # Update Badge
        pid = lock_alive()
        if pid:
            self.update_badge(f"ИДЁТ СБОР (PID {pid})")
        else:
            self.update_badge("READY")
        
        self.root.after(5000, self._refresh_loop)

def main():
    root = tk.Tk()
    app = HarvestGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()
