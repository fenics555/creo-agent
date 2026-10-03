# -*- coding: utf-8 -*-
"""Живая проба долга волны 4: редактор правил ПРАВИТ КРИТЕРИИ (раньше только порядок/вкл).

Проверяем на живом окне: выбрали правило -> загрузили критерии -> изменили ->
схема осталась в порядке. Файл rules.json на диске НЕ переписывается: проба работает
с копией документа в памяти окна и файлов не сохраняет.
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))
sys.path.insert(0, str(AGENT / "rules"))

fail = []


def ok(name, cond, detail=""):
    d = detail if isinstance(detail, str) else str(detail)
    print(("OK   " if cond else "FAIL ") + name + ((" | " + d) if d else ""))
    if not cond:
        fail.append(name)


import gui as g        # noqa: E402
import rules_engine as RE   # noqa: E402

app = g.App()
app.root.update_idletasks()
ok("окно правил собрано", app.root.winfo_exists() == 1)

# 1. выбираем первое правило и грузим критерии в поля
app.lst.selection_set(0)
app.load_criteria()
txt = app.crit.get("1.0", "end").strip()
ok("критерии выбранного правила загружены в поля", bool(txt), txt.splitlines()[0] if txt else "—")

# 2. ПРАВИМ критерий: дописываем второй (конъюнкция)
rid = app.sel()["id"]
before = len(app.sel().get("criteria") or [])
new_text = txt + "\nitem_name contains ПРОБА_КРИТЕРИЯ"
app.crit.delete("1.0", "end")
app.crit.insert("1.0", new_text)
res = app.save_criteria()
after = len(app.sel().get("criteria") or [])
ok("критерии записываются в правило", res and after == before + 1,
   "было %d, стало %d (%s)" % (before, after, rid))
ok("изменённый критерий виден в текстовом виде правил",
   "ПРОБА_КРИТЕРИЯ" in RE.all_text(app.doc), "текст правил пересобран")

# 3. НЕПОЛНЫЙ критерий не ломает правило (честный отказ)
bad_before = len(app.sel().get("criteria") or [])
app.crit.delete("1.0", "end")
app.crit.insert("1.0", "param_value")            # только тип, без операции и значения
app.save_criteria()
ok("неполный критерий не записан", len(app.sel().get("criteria") or []) == bad_before,
   "критериев осталось: %d" % len(app.sel().get("criteria") or []))

# 4. схема после правок в порядке
errs = RE.validate(app.doc)
ok("схема правил после правок в порядке", not errs, "ошибок: %d" % len(errs))

# 5. файл на диске НЕ тронут (проба ничего не сохраняет)
doc_disk = RE.load()[0]
disk_has = any("ПРОБА_КРИТЕРИЯ" in str(c)
               for r in doc_disk.get("rules", []) for c in (r.get("criteria") or []))
ok("файл rules.json на диске не изменён пробой", not disk_has,
   "проба работала с памятью окна")

app.root.destroy()
print("=== ИТОГ ПРОБЫ КРИТЕРИЕВ: %s (провалов %d) ==="
      % ("ОК" if not fail else "НЕ ОК", len(fail)))
if fail:
    print("провалы: " + "; ".join(fail))
sys.exit(1 if fail else 0)