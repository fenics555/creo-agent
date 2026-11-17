# -*- coding: utf-8 -*-
"""plm_db_admin_win.py — ГРАФИЧЕСКОЕ ОКНО «Обслуживание и аудит базы данных PLM» (V189).

ЗАЧЕМ: обычный пользователь НЕ должен помнить CLI-команды. Окно даёт кнопки с
подсказками и живой отчёт прямо в интерфейсе PLM Reader.

ЧТО УМЕЕТ (по кнопкам):
  1) Диагноз базы            — plm_database.doctor (СТРОГО read-only);
  2) Проверка схемы/индексов — plm_database.check(full=True, use_cache=False);
  3) Создать недостающие индексы — plm_database.ensure_indexes;
  4) План очистки дублей (dry-run) — plm_database.repair(dry_run=True);
  5) Очистить дубли и само-связи — plm_database.repair(dry_run=False) + БЭКАП,
     затем колбэк on_after_repair() (пересборка связей и графа);
  6) Сжать дампы unknown_fields  — plm_database.compact_unknown_fields(dry_run=False) + БЭКАП;
  7) Сжать файл базы         — plm_database.vacuum.

Все длительные операции — в фоновом потоке (окно не зависает), кнопки на время
блокируются; отчёт — в скроллируемом поле моноширинным шрифтом; кнопка
«Копировать отчёт». Модуль самодостаточный (только стандартная библиотека + Tkinter).
"""
import contextlib
import io
import os
import threading
import traceback
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk


def _db_size_mb(path):
    """Размер файла базы в МБ (0.0, если файла нет)."""
    try:
        return os.path.getsize(path) / 1024.0 / 1024.0
    except OSError:
        return 0.0


def _resolve_db_path(db_path=None):
    """Путь к БД: явный → активная база движка (engine.active_db())."""
    if db_path:
        return db_path
    try:
        import engine
        return engine.active_db()
    except Exception:
        return None


class _DBAdminWindow(tk.Toplevel):
    """Окно обслуживания и аудита базы (тяжёлые операции — в фоне)."""

    def __init__(self, parent, db_path=None, on_after_repair=None):
        super().__init__(parent)
        self.parent = parent
        self.on_after_repair = on_after_repair
        self.db_path = _resolve_db_path(db_path)
        self._busy = False
        self._buttons = []
        self.title("Обслуживание и аудит базы данных PLM")
        self.geometry("920x660")
        try:
            self.transient(parent)
        except Exception:
            pass
        self._build()
        self._refresh_header()

    # ── построение интерфейса ────────────────────────────────────────────────
    def _build(self):
        hdr = ttk.LabelFrame(self, text=" Активная база ", padding=8)
        hdr.pack(fill="x", padx=10, pady=(10, 0))
        self.hdr = ttk.Label(hdr, text="…", justify="left")
        self.hdr.pack(anchor="w")
        ttk.Label(hdr, text="Все операции ниже применяются ТОЛЬКО к этой базе.",
                  foreground="#555").pack(anchor="w", pady=(4, 0))

        body = ttk.Frame(self, padding=(10, 6))
        body.pack(fill="x")

        def add_btn(text, hint, cmd, strong=False):
            row = ttk.Frame(body)
            row.pack(fill="x", pady=2)
            b = ttk.Button(row, text=text, width=32, command=cmd)
            b.pack(side="left")
            self._buttons.append(b)
            ttk.Label(row, text=hint, foreground=("#a00" if strong else "#444"),
                      wraplength=520, justify="left").pack(side="left", padx=8)

        add_btn("Диагноз базы (только чтение)",
                "READ-ONLY: показывает отчёт, базу НЕ меняет.",
                self.act_doctor)
        add_btn("Проверка схемы и индексов",
                "READ-ONLY: целостность, схема, индексы, аудит данных.",
                self.act_check)
        add_btn("Создать недостающие индексы",
                "ИЗМЕНИТ базу: добавит индексы (строки данных не меняются).",
                self.act_ensure_indexes)
        add_btn("План очистки дублей (Dry-Run)",
                "Показывает план очистки. НИЧЕГО не меняет.",
                self.act_repair_dry)
        add_btn("Очистить дубли и само-связи",
                "СОЗДАЁТ БЭКАП и удаляет дубли/само-связи в links/graph_edges. "
                "Архивная история (changes/history/arch_*) сохраняется.",
                self.act_repair_apply, strong=True)
        add_btn("Сжать дампы unknown_fields",
                "Обрежет СТАРЫЕ длинные хвосты в unknown_fields до 512 символов, "
                "~−1.1 ГБ; затем нажмите «Vacuum».",
                self.act_compact, strong=True)
        add_btn("Выровнять регистр имён (V193)",
                "Приведёт имена моделей к единому UPPER (убирает ложные «висячие» связи). "
                "План — через Dry-Run; затем нажмите Vacuum.",
                self.act_normalize, strong=True)
        add_btn("Топ-30 неразобранных полей",
                "READ-ONLY (V215): Исторический декодер — классифицирует легаси-журнал "
                "и показывает ТОП-30 неразобранных имён полей. Базу НЕ меняет.",
                self.act_rescue)
        add_btn("Сжать файл базы (Vacuum)",
                "Может занять время; перезаписывает файл базы (бэкап не создаётся).",
                self.act_vacuum, strong=True)

        rep = ttk.LabelFrame(self, text=" Отчёт ", padding=6)
        rep.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        self.txt = scrolledtext.ScrolledText(rep, height=18, wrap="none",
                                             font=("Consolas", 9))
        self.txt.pack(fill="both", expand=True)
        bar = ttk.Frame(rep)
        bar.pack(fill="x", pady=(6, 0))
        ttk.Button(bar, text="Копировать отчёт",
                   command=self._copy_report).pack(side="left")
        ttk.Button(bar, text="Очистить отчёт",
                   command=lambda: self._log("", clear=True)).pack(side="left", padx=6)
        ttk.Button(bar, text="Закрыть", command=self.destroy).pack(side="right")

    # ── шапка/размер ─────────────────────────────────────────────────────────
    def _refresh_header(self):
        p = self.db_path
        if not p or not os.path.isfile(p):
            self.hdr.config(text="Активная база не найдена: %s" % (p or "—"))
            return
        self.hdr.config(text="База: %s\nРазмер: %.1f МБ" % (p, _db_size_mb(p)))

    def _set_enabled(self, flag):
        state = "normal" if flag else "disabled"
        for b in self._buttons:
            try:
                b.config(state=state)
            except Exception:
                pass

    def _log(self, text, clear=False):
        try:
            if clear:
                self.txt.delete("1.0", "end")
                return
            self.txt.insert("end", text)
            self.txt.see("end")
        except Exception:
            pass

    def _copy_report(self):
        try:
            self.clipboard_clear()
            self.clipboard_append(self.txt.get("1.0", "end"))
            self._log("\n[отчёт скопирован в буфер обмена]\n")
        except Exception as e:                    # noqa: BLE001
            messagebox.showwarning("Копирование", "Не удалось скопировать: %s" % e)

    # ── запуск операции в фоне ───────────────────────────────────────────────
    def _run(self, title, action, after=None):
        """Выполнить `action` в фоне, собрав её stdout в окно отчёта."""
        if self._busy:
            return
        p = self.db_path
        if not p or not os.path.isfile(p):
            messagebox.showwarning("База", "Активная база не найдена:\n%s" % (p or "—"))
            return
        self._busy = True
        self._set_enabled(False)
        self._log("\n" + "=" * 68 + "\n=== %s ===\n" % title)

        def work():
            buf = io.StringIO()
            err = None
            try:
                with contextlib.redirect_stdout(buf):
                    action()
            except Exception as e:                # noqa: BLE001
                err = e
            out = buf.getvalue()
            self.after(0, lambda: self._done(out, err, after))

        threading.Thread(target=work, daemon=True).start()

    def _done(self, out, err, after):
        self._log(out)
        if err is not None:
            self._log("\n[ОШИБКА] %s: %s\n%s\n"
                      % (type(err).__name__, err, traceback.format_exc()))
        self._log("\n=== завершено ===\n")
        self._busy = False
        self._set_enabled(True)
        self._refresh_header()
        if after and err is None:
            try:
                after()
            except Exception as e:                # noqa: BLE001
                self._log("\n[шаг после операции не удался] %s\n" % e)

    # ── операции (кнопки) ────────────────────────────────────────────────────
    def act_doctor(self):
        """READ-ONLY: подробный диагноз базы."""
        import plm_database
        self._run("Диагноз базы (только чтение)",
                  lambda: plm_database.doctor(self.db_path))

    def act_check(self):
        """READ-ONLY: целостность + схема + индексы + аудит данных."""
        import plm_database
        self._run("Проверка схемы и индексов",
                  lambda: plm_database.check(self.db_path, full=True, use_cache=False))

    def act_ensure_indexes(self):
        """Создать недостающие индексы по связующим колонкам."""
        import plm_database
        self._run("Создание недостающих индексов",
                  lambda: plm_database.ensure_indexes(self.db_path))

    def act_repair_dry(self):
        """DRY-RUN: показать план очистки связей, ничего не меняя."""
        import plm_database
        self._run("План очистки дублей (Dry-Run)",
                  lambda: plm_database.repair(self.db_path, dry_run=True))

    def act_repair_apply(self):
        """Очистка дублей/само-связей: подтверждение → repair(apply) → on_after_repair."""
        import plm_database
        if not messagebox.askyesno(
                "Очистка дублей и само-связей",
                "Будут удалены дубли пар и само-связи в таблицах links и graph_edges.\n\n"
                "• Сначала создаётся БЭКАП базы.\n"
                "• Архивная история (changes, history, arch_dims, arch_dim_ch) НЕ трогается.\n"
                "• После очистки будут пересобраны связи и граф.\n\n"
                "Продолжить?"):
            return
        self._run("Очистка дублей и само-связей",
                  lambda: plm_database.repair(self.db_path, dry_run=False),
                  after=self.on_after_repair)

    def act_compact(self):
        """Сжатие СТАРЫХ длинных дампов `unknown_fields` (с подтверждением)."""
        import plm_database
        if not messagebox.askyesno(
                "Сжать дампы unknown_fields",
                "Будут ОБРЕЗАНЫ длинные значения (столбец `model`) в таблице unknown_fields —\n"
                "до 512 символов (сохраняются ключи и счётчики полей).\n\n"
                "• Таблица раздулась из-за сырых JSON-дампов (~20 КБ на файл).\n"
                "• Сначала создаётся БЭКАП базы.\n"
                "• Место на диске вернёт последующая команда Vacuum.\n\n"
                "Продолжить?"):
            return
        self._run("Сжатие дампов unknown_fields",
                  lambda: plm_database.compact_unknown_fields(self.db_path, dry_run=False))

    def act_normalize(self):
        """V193: выравнивание регистра имён моделей к единому UPPER-канону."""
        import plm_database
        if not messagebox.askyesno(
                "Выровнять регистр имён (V193)",
                "Имена моделей будут приведены к единому UPPER-канону во всех ключевых колонках.\n\n"
                "• Сначала создаётся БЭКАП базы.\n"
                "• Архивная история (changes/history/arch_*) НЕ трогается.\n"
                "• Строки не удаляются (кроме технических дублей при конфликте ключа).\n\n"
                "Продолжить?"):
            return
        self._run("Выравнивание регистра имён",
                  lambda: plm_database.normalize_case(self.db_path, dry_run=False))

    def act_rescue(self):
        """V215: READ-ONLY превью Исторического декодера — ТОП-30 неразобранных имён полей."""
        import plm_database
        self._run("Топ-30 неразобранных полей (Исторический декодер)",
                  lambda: plm_database.rescue_legacy_data(self.db_path, dry_run=True))

    def act_vacuum(self):
        """Сжать файл базы (VACUUM) с подтверждением."""
        import plm_database
        if not messagebox.askyesno(
                "Сжатие файла базы (Vacuum)",
                "Файл базы будет перезаписан (уменьшен).\n"
                "Во время сжатия база недоступна другим.\n"
                "Бэкап автоматически НЕ создаётся.\n\nПродолжить?"):
            return
        self._run("Сжатие файла базы (Vacuum)",
                  lambda: plm_database.vacuum(self.db_path))


def open_db_admin_window(parent, db_path=None, on_after_repair=None):
    """Открыть окно «Обслуживание и аудит БД». Возвращает объект окна (или None)."""
    try:
        return _DBAdminWindow(parent, db_path=db_path, on_after_repair=on_after_repair)
    except Exception as e:                        # noqa: BLE001
        try:
            messagebox.showwarning("Аудит / БД",
                                   "Не удалось открыть окно обслуживания:\n%s" % e)
        except Exception:
            pass
        return None
