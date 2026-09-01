# -*- coding: utf-8 -*-
r"""АГЕНТ v12 — БЛОК CREO-ОПЕРАЦИЙ (creo_ops_tools.py)
Пишущие операции над живым Creo — ВСЕ под щитом согласования.
creo_set_relations: mode=merge — старые уравнения сохраняются
(совпадающие по левой части заменяются), append — дописать, replace — перезапись.
"""
import re
from pathlib import Path
import core
import creo_tools as CT

ok, errmsg, cc = CT.ok, CT.errmsg, CT.creo_call

def _rel_lhs(line):
    s = line.strip()
    m = re.match(r"^([A-Za-zА-Яа-я_][A-Za-zА-Яа-я0-9_]*)\s*=(?!=)", s)
    return (m.group(1) if m else s).upper()

def tool_set_param(name="", value="", model="", **kw):
    m = model or CT.tool_get_active()
    j = cc("parameter", "set", {"file": m, "name": name, "value": value}, 20)
    return "параметр %s=%s установлен на %s" % (name, value, m) if ok(j) else "не установилось: %s" % errmsg(j)

def tool_set_relations(relations="", mode="merge", model="", **kw):
    m = model or CT.tool_get_active()
    if isinstance(relations, list): relations = "\n".join(str(x) for x in relations)
    new_lines = [ln.strip() for ln in str(relations).replace("\r", "").split("\n") if ln.strip()]
    if not new_lines: return "нечего писать: relations пустые"
    if mode in ("merge", "append"):
        j0 = cc("file", "relations_get", {"file": m}, 20)
        old_text = ""
        if ok(j0):
            d = j0.get("data")
            old_text = d if isinstance(d, str) else (d or {}).get("relations") or ""
        old_lines = [ln.rstrip() for ln in old_text.replace("\r", "").split("\n") if ln.strip()]
        if mode == "merge":
            new_lhs = {_rel_lhs(l) for l in new_lines}
            keep = [l for l in old_lines if _rel_lhs(l) not in new_lhs]
        else:
            keep = old_lines
        merged = keep + new_lines
    else:
        merged = new_lines
    j = cc("file", "relations_set", {"file": m, "relations": "\n".join(merged)}, 30)
    if not ok(j): return "relations не записались: %s" % errmsg(j)
    r = cc("file", "regenerate", {"file": m}, 30)
    return "relations записаны: %d строк (режим %s), регенерация %s" % (
        len(merged), mode, "ОК" if ok(r) else "с ошибкой: %s" % errmsg(r))

def tool_regenerate(name="", **kw):
    m = name or CT.tool_get_active()
    j = cc("file", "regenerate", {"file": m}, 30)
    return "регенерация %s: %s" % (m, "ОК" if ok(j) else errmsg(j))

def tool_save(name="", **kw):
    m = name or CT.tool_get_active()
    j = cc("file", "save", {"file": m}, 20)
    return "сохранено: %s" % m if ok(j) else "не сохранилось: %s" % errmsg(j)

def tool_erase(name="", **kw):
    j = cc("file", "erase", {"file": name}, 15)
    return "выгружено из памяти: %s" % name if ok(j) else "не выгрузилось: %s" % errmsg(j)

def tool_rename_model(old_name="", new_name="", **kw):
    if not old_name or not new_name: return "нужны old_name и new_name"
    old_b = re.sub(r"\.(prt|asm|drw)(\.\d+)?$", "", old_name, flags=re.I)
    new_b = re.sub(r"\.(prt|asm|drw)(\.\d+)?$", "", new_name, flags=re.I)
    opened = []
    for ext in ("prt", "drw"):
        if ok(cc("file", "open", {"file": "%s.%s" % (old_b, ext), "display": True}, 30)):
            opened.append("%s.%s" % (old_b, ext))
    if not opened: return "не смог открыть %s ни как .prt, ни как .drw" % old_b
    for f in opened:
        j = cc("file", "rename", {"file": f, "new_name": new_b, "rename_dependencies": True}, 30)
        if not ok(j): return "rename %s не удался: %s" % (f, errmsg(j))
    cc("drawing", "regenerate", {"drawing": "%s.drw" % new_b}, 30)
    for f in opened:
        cc("file", "save", {"file": f.replace(old_b, new_b)}, 20)
    return "переименовано %s → %s (%s); чертёж регенерирован; сохранено" % (old_b, new_b, ", ".join(opened))

def tool_purge_versions(**kw):
    wd = CT.tool_pwd()
    if not wd: return "не узнал рабочую папку"
    groups = {}
    for p in Path(wd).glob("*.*"):
        m = re.match(r"^(.+?\.(?:prt|asm|drw))\.(\d+)$", p.name, re.I)
        if m: groups.setdefault(m.group(1), []).append((int(m.group(2)), p))
    killed = 0
    for base, vers in groups.items():
        vers.sort()
        for _, p in vers[:-1]:
            try: p.unlink(); killed += 1
            except Exception: pass
    return "склад версий в %s: удалено %d старых, оставлены последние" % (wd, killed)

def tool_print_pdf(name="", dirname="", **kw):
    nm = name or CT.tool_get_active()
    outdir = dirname or str(core.BASE / "pdf_out")
    Path(outdir).mkdir(parents=True, exist_ok=True)
    pdf = re.sub(r"\.(asm|prt|drw)(\.\d+)?$", "", nm, flags=re.I) + ".pdf"
    j = cc("interface", "export_pdf", {"file": nm, "filename": pdf, "dirname": outdir,
                                       "use_drawing_settings": True, "sheet_range": "all"}, 60)
    if not ok(j): return "экспорт PDF не удался: %s" % errmsg(j)
    return "PDF сохранён: %s" % str(Path(outdir) / pdf)

def tool_mapkey(script="", **kw):
    j = cc("interface", "mapkey", {"script": script}, 60)
    return "mapkey выполнен" if ok(j) else "mapkey не выполнен: %s" % errmsg(j)

def tool_kill(**kw):
    j = cc("connection", "kill_creo", {}, 30)
    return "Creo остановлен жёстко" if ok(j) else "не остановилось: %s" % errmsg(j)

def tool_start(**kw):
    j = cc("connection", "start_creo", {}, 120)
    return "Creo запускается" if ok(j) else "не запустилось: %s" % errmsg(j)

def tool_stop(**kw):
    j = cc("connection", "stop_creo", {}, 60)
    return "Creo остановлен корректно" if ok(j) else "не остановилось: %s" % errmsg(j)

def tool_assemble(files="", **kw):
    lst = [x.strip() for x in str(files).split(",") if x.strip()]
    j = cc("file", "assemble", {"files": lst}, 60)
    return "добавлено в сборку: %s" % ", ".join(lst) if ok(j) else "не собралось: %s" % errmsg(j)

def tool_set_units(units="mm", model="", **kw):
    m = model or CT.tool_get_active()
    j = cc("file", "set_length_units", {"file": m, "units": units}, 20)
    return "единицы %s установлены на %s" % (units, m) if ok(j) else "не установилось: %s" % errmsg(j)

def tool_backup(name="", dirname="", **kw):
    m = name or CT.tool_get_active()
    outdir = dirname or str(core.BASE / "backup_models")
    Path(outdir).mkdir(parents=True, exist_ok=True)
    j = cc("file", "backup", {"file": m, "dirname": outdir}, 30)
    return "бэкап %s в %s" % (m, outdir) if ok(j) else "бэкап не удался: %s" % errmsg(j)

def tool_draw_regenerate(drawing="", **kw):
    j = cc("drawing", "regenerate", {"drawing": drawing}, 30)
    return "чертёж %s регенерирован" % drawing if ok(j) else "регенерация чертежа не удалась: %s" % errmsg(j)

TOOLS = [
    {"name": "creo_set_param", "desc": "Установить параметр модели Creo", "params": {"name": "имя", "value": "значение", "model": "модель"}, "approval": True, "fn": tool_set_param},
    {"name": "creo_set_relations", "desc": "Записать отношения и регенерировать. mode: merge — старые сохраняются (совпадающие по левой части заменяются), append — дописать, replace — перезапись", "params": {"relations": "код", "mode": "merge/append/replace", "model": "модель"}, "approval": True, "fn": tool_set_relations},
    {"name": "creo_regenerate", "desc": "Регенерация модели в Creo", "params": {"name": "имя модели"}, "approval": True, "fn": tool_regenerate},
    {"name": "creo_save", "desc": "Сохранить модель в Creo", "params": {"name": "имя модели"}, "approval": True, "fn": tool_save},
    {"name": "creo_erase", "desc": "Выгрузить модель из памяти Creo", "params": {"name": "имя модели"}, "approval": True, "fn": tool_erase},
    {"name": "creo_rename_model", "desc": "Умное переименование: открыть чертёж и сборки, переименовать деталь и чертёж, регенерировать, сохранить", "params": {"old_name": "старое", "new_name": "новое"}, "approval": True, "fn": tool_rename_model},
    {"name": "creo_purge_versions", "desc": "Чистка склада версий: удалить старые .prt/.asm/.drw, оставить последнюю", "params": {}, "approval": True, "fn": tool_purge_versions},
    {"name": "creo_print_pdf", "desc": "Экспорт в PDF в заданную папку (pdf_out) с настройками чертежа", "params": {"name": "чертёж", "dirname": "папка"}, "approval": True, "fn": tool_print_pdf},
    {"name": "creo_mapkey", "desc": "Выполнить mapkey-скрипт в Creo (адаптация/автоматизация)", "params": {"script": "текст mapkey"}, "approval": True, "fn": tool_mapkey},
    {"name": "creo_kill", "desc": "Остановить Creo жёстко", "params": {}, "approval": True, "fn": tool_kill},
    {"name": "creo_start", "desc": "Запустить Creo", "params": {}, "approval": True, "fn": tool_start},
    {"name": "creo_stop", "desc": "Остановить Creo корректно", "params": {}, "approval": True, "fn": tool_stop},
    {"name": "creo_assemble", "desc": "Добавить компоненты в активную сборку", "params": {"files": "имена через запятую"}, "approval": True, "fn": tool_assemble},
    {"name": "creo_set_units", "desc": "Установить единицы длины модели", "params": {"units": "mm/in", "model": "модель"}, "approval": True, "fn": tool_set_units},
    {"name": "creo_backup", "desc": "Резервная копия модели в папку", "params": {"name": "модель", "dirname": "папка"}, "approval": True, "fn": tool_backup},
    {"name": "creo_draw_regenerate", "desc": "Регенерация чертежа", "params": {"drawing": "имя чертежа"}, "approval": True, "fn": tool_draw_regenerate},
]