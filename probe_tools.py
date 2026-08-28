# -*- coding: utf-8 -*-
r"""АГЕНТ v12 — ПРОБНИК БЛОКОВ: все инструменты всех блоков, живой отклик."""
import importlib, time
import core
from core import log
import tools_registry as TR

REPORT = core.BASE / "block_probe_report.txt"
SKIP = {"probe_run", "behavior_run", "diag_run", "diag_test", "creo_audit_folder",
        "index_run", "scan_run", "backup_restore", "web_fetch", "vision_analyze",
        "creo_open", "creo_mapkey", "creo_kill", "creo_start", "creo_stop",
        "creo_purge_versions", "creo_rename_model", "creo_print_pdf",
        "creo_set_relations", "creo_set_param", "creo_save", "creo_erase",
        "creo_regenerate", "creo_assemble", "creo_set_units", "creo_backup",
        "creo_draw_regenerate", "user_add", "user_role", "settings_set"}

def run():
    per = {}
    for b in TR.BLOCKS:
        try:
            m = importlib.import_module(b)
            for t in getattr(m, "TOOLS", []): per.setdefault(b, []).append(t)
        except Exception: pass
    lines = ["=== ПРОБНИК БЛОКОВ %s ===" % time.strftime("%d.%m.%Y %H:%M")]
    ok = err = skip = 0
    for b in sorted(per):
        lines.append("■ %s (%d)" % (b, len(per[b])))
        for t in sorted(per[b], key=lambda x: x["name"]):
            n = t["name"]
            if t.get("approval"):
                lines.append("  [W] %s — пишущий (fn=%s)" % (n, "есть" if callable(t.get("fn")) else "НЕТ")); skip += 1; continue
            if n in SKIP:
                lines.append("  [-] %s — пропуск" % n); skip += 1; continue
            t0 = time.time()
            try:
                try: r = str(t["fn"]())
                except TypeError: r = str(t["fn"](**{k: "" for k in t.get("params", {})}))
                ms = int((time.time() - t0) * 1000)
                if not r.strip(): mark, note = "X", "пусто"
                elif r.startswith("ошибка"): mark, note = "X", r[:60]
                else: mark, note = "OK", r[:50].replace("\n", " ")
            except Exception as e:
                mark, note, ms = "X", "исключение: %s" % e, int((time.time() - t0) * 1000)
            if mark == "OK": ok += 1
            else: err += 1
            lines.append("  %s %s — %s (%dмс)" % (mark, n, note, ms))
    lines.append("ИТОГО: OK %d | пропущено %d | X %d" % (ok, skip, err))
    try: REPORT.write_text("\n".join(lines), encoding="utf-8")
    except Exception: pass
    log("пробник: ok %d bad %d, пропущено %d" % (ok, err, skip))
    return "\n".join(lines)

TOOLS = [{"name": "probe_run", "desc": "Автопрогон всех инструментов всех блоков", "params": {}, "approval": False, "fn": lambda **kw: run()}]