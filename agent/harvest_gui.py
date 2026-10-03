# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sys
import ctypes
from pathlib import Path
from harvest_gui_panels import AppPanelsMixin

# Каркас окон дома. 03.10.2026 (дизайн по конспекту ОКНА): у окна НЕ БЫЛО заголовка с
# версией, minsize и README-кнопки — три признака канона. Теперь даёт их каркас.
_AGENT_ROOT = Path(__file__).resolve().parent
if str(_AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_AGENT_ROOT))
import ui_common as U  # noqa: E402

# Constants (Davydovka Palette)
BG = U.BG
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
# ЖИВАЯ НАХОДКА 03.10.2026 (аудит data\, Д4): журнал был ещё и тут (data\harvest.log), а harvest.py писал в D:\AI\log\harvest\ — два файла одного журнала. Теперь одна цель.
LOGF = r'D:\AI\log\harvest\harvest.log'

def lock_alive():
    if not os.path.exists(LOCK):
        return None
    try:
        with open(LOCK, 'r', encoding='utf-8') as f:
            pid_str = f.read().strip()
            if not pid_str:
                return None
            pid = int(pid_str)
            if pid and ctypes.windll.kernel32.OpenProcess(0x1000, False, pid):
                return pid
    except Exception:
        pass
    return None

class HarvestGUI(AppPanelsMixin):
    def __init__(self, root):
        self.root = root
        # 03.10.2026: были title='Harvest GUI' без версии и geometry без minsize —
        # окно можно было сжать в полосу. Теперь заголовок по канону и минимальный размер.
        self.root.title('V2 — СБОР ДАННЫХ (harvest)')
        self.root.geometry('1020x640')
        self.root.minsize(760, 520)
        self.root.configure(bg=BG)
        self._build_info_panel()
        self._setup_controls()
        self._refresh_loop()

    def _setup_controls(self):
        ctrl = tk.Frame(self.root, bg=BG)
        ctrl.pack(fill='x', padx=5, pady=5)
        # КАНОН ОКНА: README-кнопка обязательна (манифест п.19 — окно самостоятельно).
        # Свой мини-вариант, потому что README программы лежит как `HARVEST_README.md`,
        # а каркас ищет `README.md` (у harvest нет своей папки — движок лежит в корне агента).
        tk.Button(ctrl, text='README', width=12, command=self._show_readme,
                  bg=BG, relief='flat', fg=U.ACCENT, cursor='hand2').pack(side='right', padx=4)
        self.stop_btn = tk.Button(ctrl, text='СТОП', command=self.on_stop, bg='#ff4444', fg='white')
        self.stop_btn.pack(side='right')
        self.badge_lbl = tk.Label(ctrl, text='', bg=CARD, relief='sunken')
        self.badge_lbl.pack(side='left', padx=5)

    def _show_readme(self):
        """README программы в лог окна (канон: при ошибке — честная строка, не падение)."""
        p = Path(__file__).resolve().parent / 'HARVEST_README.md'
        try:
            text = p.read_text(encoding='utf-8')
        except Exception as e:
            return self._log('README не прочитан: %s' % e)
        self._log('=' * 90)
        for line in text.splitlines():
            self._log(line)
        self._log('=' * 90)
        self._log('конец README')

    def _log(self, msg=''):
        """Каркасный лог окна: пишем в текст панели, если он уже создан."""
        try:
            self.log_txt.configure(state='normal')
            self.log_txt.insert('end', str(msg) + '\n')
            self.log_txt.see('end')
            self.log_txt.configure(state='disabled')
        except Exception:
            pass

    def update_badge(self, text):
        self.badge_lbl.configure(text=text)

    def _refresh_loop(self):
        super()._refresh_loop()
        pid = lock_alive()
        self.update_badge(f"ИДЁТ СБОР (PID {pid})" if pid else "READY")
        self.root.after(5000, self._refresh_loop)

def main():
    root = tk.Tk()
    app = HarvestGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()
