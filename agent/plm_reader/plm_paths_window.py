# -*- coding: utf-8 -*-
"""plm_paths_window.py — вынесено из plm_reader.py распилом (см. СПЕКА_РАСПИЛА_PLM_READER.md)."""
from plm_reader import (
    norm_path,
    os,
    save_settings_file,
)


class PathsWindow:
    """Окно «Пути и исключения…»: папки сканирования, папки-исключения и ГДЕ ЖИВЁТ БАЗА.

    «＋» добавляет строку, «−» удаляет; пустые строки и дубли отбрасываются при сохранении
    (поэтому запятые в именах папок ничему не мешают)."""

    def __init__(self, parent, settings, tk, ttk, filedialog, on_save=None):
        self.tk, self.ttk, self.filedialog = tk, ttk, filedialog
        self.settings = settings
        self.on_save = on_save
        self.win = tk.Toplevel(parent)
        self.win.title("Пути, исключения и база данных")
        self.win.geometry("860x720")
        self.win.transient(parent)
        self.rows = {"folders": [], "exclude": [], "template_folders": [], "db_mirror": []}
        box = ttk.Frame(self.win, padding=10)
        box.pack(fill="both", expand=True)
        ttk.Label(box, text="Папки сканирования (одна строка = один путь):",
                  font=("", 10, "bold")).pack(anchor="w")
        self.sec_scan = self._section(box, "folders")
        ttk.Label(box, text="ШАБЛОНЫ:", font=("", 10, "bold")).pack(anchor="w", pady=(14, 0))
        self.sec_tpl = self._section(box, "template_folders")
        ttk.Label(box, text="Папки исключений — НЕ читать вовсе (одна строка = один путь):",
                  font=("", 10, "bold")).pack(anchor="w", pady=(14, 0))
        self.sec_exc = self._section(box, "exclude")
        ttk.Label(box, text="ГДЕ ЖИВЁТ БАЗА", font=("", 10, "bold")).pack(anchor="w", pady=(14, 0))
        ttk.Label(box, text="Пусто = рядом с программой, в папке db\\. Можно указать другой диск:",
                  foreground="#555").pack(anchor="w")
        dline = ttk.Frame(box)
        dline.pack(fill="x", pady=(2, 0))
        self.e_db_dir = ttk.Entry(dline)
        self.e_db_dir.insert(0, settings.get("db_dir") or "")
        self.e_db_dir.pack(side="left", fill="x", expand=True)
        ttk.Button(dline, text="Выбрать…", width=10,
                   command=lambda: self._pick(self.e_db_dir)).pack(side="left", padx=4)
        ttk.Label(box, text="Зеркала базы (другая машина/диск): свежая база копируется туда. "
                            "Пусто = не дублировать:",
                  foreground="#555").pack(anchor="w", pady=(8, 0))
        self.sec_mir = self._section(box, "db_mirror")
        mrow = ttk.Frame(box)
        mrow.pack(fill="x", pady=(4, 0))
        ttk.Label(mrow, text="хранить свежих баз в зеркале:").pack(side="left")
        self.sp_mkeep = ttk.Spinbox(mrow, from_=1, to=50, width=4)
        self.sp_mkeep.set(str(settings.get("mirror_keep") or 3))
        self.sp_mkeep.pack(side="left", padx=(4, 14))
        self.var_mfull = tk.BooleanVar(value=bool(settings.get("mirror_full_only", True)))
        ttk.Checkbutton(mrow, text="зеркалить только после ПОЛНОГО скана",
                        variable=self.var_mfull).pack(side="left")
        self.mir_now = ttk.Button(box, text="Скопировать базу в зеркала ПРЯМО СЕЙЧАС",
                                  command=self.copy_now)
        self.mir_now.pack(anchor="w", pady=(6, 0))
        foot = ttk.Frame(box)
        foot.pack(fill="x", pady=(12, 0))
        ttk.Button(foot, text="Сохранить", command=self.save).pack(side="left")
        ttk.Button(foot, text="Закрыть", command=self.win.destroy).pack(side="left", padx=6)
        self.msg = ttk.Label(foot, text="", foreground="#555")
        self.msg.pack(side="left", padx=10)
        p_folders = settings.get("folders") or []
        for p in p_folders:
            self.add_row("folders", p)
        for p in (settings.get("exclude") or []):
            self.add_row("exclude", p)
        for p in (settings.get("template_folders") or []):
            self.add_row("template_folders", p)
        for p in (settings.get("db_mirror") or []):
            self.add_row("db_mirror", p)
        if not self.rows["folders"]:
            self.add_row("folders", "")
        if not self.rows["exclude"]:
            self.add_row("exclude", "")
        if not self.rows["template_folders"]:
            self.add_row("template_folders", "")
        if not self.rows["db_mirror"]:
            self.add_row("db_mirror", "")

    def _section(self, parent, key):
        fr = self.ttk.Frame(parent)
        fr.pack(fill="x", pady=(4, 0))
        self.ttk.Button(fr, text="＋ папка", width=12,
                        command=lambda: self.add_row(key, "")).pack(anchor="w", pady=(0, 2))
        holder = self.ttk.Frame(fr)
        holder.pack(fill="x")
        return holder

    def add_row(self, key, path):
        holder = {"folders": self.sec_scan, "exclude": self.sec_exc,
                  "template_folders": self.sec_tpl,
                  "db_mirror": self.sec_mir}.get(key, self.sec_scan)
        line = self.ttk.Frame(holder)
        line.pack(fill="x", pady=1)
        ent = self.ttk.Entry(line)
        ent.insert(0, path or "")
        ent.pack(side="left", fill="x", expand=True)
        self.ttk.Button(line, text="Выбрать…", width=10,
                        command=lambda e=ent: self._pick(e)).pack(side="left", padx=4)
        self.ttk.Button(line, text="−", width=3,
                        command=lambda l=line, k=key: self.del_row(k, l)).pack(side="left")
        self.rows[key].append((line, ent))

    def del_row(self, key, line):
        self.rows[key] = [(l, e) for (l, e) in self.rows[key] if l is not line]
        line.destroy()

    def _pick(self, ent):
        d = self.filedialog.askdirectory(initialdir=ent.get() or os.path.expanduser("~"))
        if d:
            ent.delete(0, "end")
            ent.insert(0, d.replace("/", "\\"))

    def collect(self):
        """Списки путей: пустые строки и дубли (без учёта регистра) отбрасываются."""
        out = {}
        for key in ("folders", "exclude", "template_folders", "db_mirror"):
            seen, vals = set(), []
            for _line, ent in self.rows[key]:
                v = norm_path(ent.get())
                if v and v.lower() not in seen:
                    seen.add(v.lower())
                    vals.append(v)
            out[key] = vals
        return out

    def copy_now(self):
        """Прогнать зеркалирование без скана: копия свежей базы — по кнопке."""
        import engine as _e
        self.save()                                  # сначала сохранить пути, что введены
        src = _e.active_db()
        if not os.path.isfile(src):
            self.msg.config(text="нечего копировать: базы ещё нет (нажми Сканировать)")
            return
        try:
            done = _e.mirror_published(src)
        except Exception as ex:
            self.msg.config(text="не удалось: %s" % ex)
            return
        if done:
            self.msg.config(text="скопировано в зеркал: %d (%s)" % (len(done), os.path.basename(src)))
        else:
            self.msg.config(text="зеркала не заданы или совпадают с рабочей папкой")

    def save(self):
        d = self.collect()
        old_dir = (self.settings.get("db_dir") or "").strip()
        self.settings["folders"] = d["folders"]
        self.settings["exclude"] = d["exclude"]
        self.settings["template_folders"] = d["template_folders"]
        self.settings["db_dir"] = norm_path(self.e_db_dir.get())
        self.settings["db_mirror"] = d["db_mirror"]
        try:
            self.settings["mirror_keep"] = max(1, min(50, int(self.sp_mkeep.get() or 3)))
        except Exception:
            self.settings["mirror_keep"] = 3
        self.settings["mirror_full_only"] = bool(self.var_mfull.get())
        save_settings_file(self.settings)
        try:
            import engine as _e
            _e.reset_service_cache()          # папки шаблонов изменились — сбросить кэш служебных
        except Exception:
            pass
        tail = ""
        new_dir = self.settings["db_dir"]
        if new_dir != old_dir:
            # папка базы поменялась — предупреждаем честно: подхватка только при перезапуске окна
            tail = " · база переедет на %s — ПЕРЕЗАПУСТИ окно" % (new_dir or "папку db\\")
        self.msg.config(text="сохранено: папок %d, исключений %d, шаблонов %d, зеркал %d%s"
                             % (len(d["folders"]), len(d["exclude"]), len(d["template_folders"]),
                                len(d["db_mirror"]), tail))
        if self.on_save:
            try:
                self.on_save()
            except Exception:
                pass
