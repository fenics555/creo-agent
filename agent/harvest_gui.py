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
    def __init__(self, root=None):
        # ПЕРЕВОД НА КАРКАС ДО КОНЦА 04.10.2026. 03.10.2026 окно было переведено наполовину:
        # импорт каркаса появился, но окно по-прежнему создавалось вручную (title/geometry/
        # minsize тремя строками), а лог и README остались самодельными. Теперь каркас даёт
        # окно и кнопку README целиком, лог окна — моноширинная панель каркаса.
        self.root = root or U.make_root('V3 — СБОР ДАННЫХ (harvest)', '1020x640',
                                        minsize=(760, 520))
        self._build_info_panel()
        self._setup_controls()
        self._refresh_loop()

    def _setup_controls(self):
        ctrl = tk.Frame(self.root, bg=BG)
        ctrl.pack(fill='x', padx=5, pady=5)
        # КАНОН ОКНА: README-кнопка обязательна (манифест п.19 — окно самостоятельно).
        # 04.10.2026: своя кнопка удалена — README теперь даёт каркас (U.readme_button).
        # ВАЖНО: программа лежит в корне агента, её собственный паспорт назван
        # HARVEST_README.md (чтобы не путать с README.md агента), поэтому каркасная кнопка
        # показывает README дома, а путь к HARVEST_README.md пишется в журнал при старте.
        U.readme_button(ctrl, str(_AGENT_ROOT), self._log)
        self.stop_btn = tk.Button(ctrl, text='СТОП', command=self.on_stop, bg='#ff4444', fg='white')
        self.stop_btn.pack(side='right')
        self.badge_lbl = tk.Label(ctrl, text='', bg=CARD, relief='sunken')
        self.badge_lbl.pack(side='left', padx=5)

    def _log(self, msg=''):
        """Журнал окна — моноширинная панель каркаса (признак канона «логи Consolas 9»).

        Панель создаётся ОДИН раз (лениво: каркасную панель надо создавать после сборки
        окна, а `readme_button` зовётся раньше). ГРАБЛЯ МОЕЙ ПЕРВОЙ ПРАВКИ (04.10.2026):
        без проверки `hasattr` панель создавалась бы заново на КАЖДОЕ сообщение —
        окно заросло бы десятками одинаковых рамок."""
        if not hasattr(self, '_logfn'):
            self._logbox, self._logfn = U.log_view(self.root, height=8, title='ЖУРНАЛ')
        self._logfn(msg)

    # Методы `_show_readme` и старый `_log` удалены 04.10.2026:
    #   · README-кнопку даёт каркас (U.readme_button), свой дубль остался бы мёртвым кодом;
    #   · старый `_log` писал в самодельный `self.log_txt`, а каркасная панель создаётся выше —
    #     оставься оба, нижний перебил бы верхний (Python: последнее определение побеждает).

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
