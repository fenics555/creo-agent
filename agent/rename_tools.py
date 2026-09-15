# -*- coding: utf-8 -*-
r"""RENAME v3: переименование модели и её чертежа через CREOSON.

Механизм доказан живыми пробами 15.09.2026 (probe gate4/gate5):
  * file:rename БЕЗ onlysession = дисковое переименование -> падает:
    «A Pro/TOOLKIT error has occurred: General Error»;
  * file:rename {onlysession:true} = сессионное переименование: ссылки в
    родительских сборках переключаются в памяти, диск не трогается;
  * file:save после него пишет файл ПОД НОВЫМ ИМЕНЕМ (старая версия остаётся
    на диске и уводится в backup, а не удаляется).
Порядок (ERR 2.8): чертёж и родители грузятся ДО rename, сохраняются снизу
вверх, чертёж последним. Гигиена (ERR 2.2): сессия проверяется до и после,
никогда не полагаемся на erase_not_displayed.
"""
import datetime
import re
import shutil
from pathlib import Path

import core
import creo_tools as CT
import settings

ok, errmsg, cc = CT.ok, CT.errmsg, CT.creo_call


def _wd():
    d = cc("creo", "pwd", {}, 10)
    if not ok(d):
        return ""
    dd = d.get("data") or {}
    s = str(dd.get("dirname") or dd.get("directory") or "").replace("/", "\\")
    if len(s) > 3 and s[0].isalpha() and s[1] == ":" and s[3] == ":":
        s = s[2:]  # CREOSON отдаёт удвоенный диск «Z:Z:/...»
    return s.rstrip("\\") or ""


def _base(name):
    return re.sub(r"\.(prt|asm|drw)(\.\d+)?$", "", str(name or "").strip(), flags=re.I)


def _latest(wd, base, ext):
    best, bv = None, -1
    for p in Path(wd).glob(base + ext + ".*"):
        v = p.name.rsplit(".", 1)[-1]
        if v.isdigit() and int(v) > bv:
            bv, best = int(v), p
    return best


def _source_ext(wd, base):
    for ext in (".prt", ".asm"):
        if _latest(wd, base, ext):
            return ext
    return ""


def _versions(wd, base):
    out = []
    for ext in (".prt", ".asm", ".drw"):
        for p in Path(wd).glob(base + ext + ".*"):
            if p.name.rsplit(".", 1)[-1].isdigit():
                out.append(p)
    return sorted(out)


def _session():
    j = cc("file", "list", {}, 10)
    return [f for f in ((j.get("data") or {}).get("files") or []) if f]


def _parents(wd, base):
    """Родительские сборки модели по базе usage (child -> parent)."""
    names = []
    try:
        c = core.db()
        rows = c.execute(
            "SELECT DISTINCT parent FROM usage WHERE child=?", (base.lower(),)
        ).fetchall()
        c.close()
        names = [r[0] for r in rows if r and r[0]]
    except Exception:
        names = []
    out = []
    for p in names:
        pb = _base(p)
        if pb and pb.lower() != base.lower() and _latest(wd, pb, ".asm"):
            if pb not in out:
                out.append(pb)
    return out


def build_plan(old="", new="", drawings=1):
    """План операции (только чтение): что переименуется и что сохранётся."""
    old_b, new_b = _base(old), _base(new)
    if not old_b or not new_b:
        return {"error": "нужны old и new"}
    if not re.match(r"^[A-Za-z0-9_\-<>]+$", new_b):
        return {"error": "новое имя: латиница/цифры/_-, без пробелов"}
    if old_b.lower() == new_b.lower():
        return {"error": "новое имя совпадает со старым"}
    wd = _wd()
    if not wd:
        return {"error": "не определил рабочую папку Creo (нет сессии CREOSON)"}
    ext = _source_ext(wd, old_b)
    if not ext:
        return {"error": "в %s нет файлов %s (prt/asm)" % (wd, old_b)}
    conflict = []
    for e in (ext, ".drw"):
        if list(Path(wd).glob(new_b + e + ".*")):
            conflict.append(new_b + e)
    rows = [{"old": old_b + ext, "new": new_b + ext, "kind": "модель"}]
    if str(drawings) in ("1", "true", "да") and _latest(wd, old_b, ".drw"):
        rows.append({"old": old_b + ".drw", "new": new_b + ".drw", "kind": "чертёж"})
    parents = _parents(wd, old_b)
    return {
        "wd": wd,
        "ext": ext,
        "rows": rows,
        "parents": parents,
        "conflict": conflict,
        "total": len(rows),
        "session": _session(),
    }


def _rename_session(file_name, new_base):
    """Сессионное переименование — единственный работающий в async CREOSON путь."""
    j = cc("file", "rename", {"file": file_name, "new_name": new_base, "onlysession": True}, 30)
    return ok(j), errmsg(j)


def _open(file_name):
    return ok(cc("file", "open", {"file": file_name, "display": False}, 30))


def _save(file_name):
    return ok(cc("file", "save", {"file": file_name}, 20))


def _erase(file_name):
    try:
        cc("file", "erase", {"file": file_name}, 10)
    except Exception:
        pass


def _park_old_versions(wd, base, log):
    """Старые версии модели и чертежа — в backup (не удаляем, урок 4.1)."""
    target = Path(settings.get("backup_dir") or (core.DATA_DIR / "backups")) / (
        "rename_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    )
    moved = 0
    try:
        target.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        log.append("backup-папка не создалась: %s" % str(e)[:60])
        return target, 0
    for p in _versions(wd, base):
        try:
            shutil.move(str(p), str(target / p.name))
            moved += 1
        except Exception as e:
            log.append("не увёл в backup %s: %s" % (p.name, str(e)[:60]))
    return target, moved


def tool_rename_model(old_name="", new_name="", drawings=1, parents=1, dry_run=1, **kw):
    plan = build_plan(old_name, new_name, drawings)
    if "error" in plan:
        return plan["error"]
    old_b, new_b, wd, ext = _base(old_name), _base(new_name), plan["wd"], plan["ext"]
    if plan["conflict"]:
        return "цель уже существует: %s — выберите другое имя" % ", ".join(plan["conflict"])
    draw = str(drawings) in ("1", "true", "да") and any(r["kind"] == "чертёж" for r in plan["rows"])
    par = list(plan["parents"]) if str(parents) in ("1", "true", "да") else []
    if str(dry_run) in ("1", "true", "да"):
        out = ["ПЛАН переименования %s -> %s (папка %s)" % (old_b, new_b, wd)]
        out += ["- %s -> %s (%s)" % (r["old"], r["new"], r["kind"]) for r in plan["rows"]]
        out.append("- сохранить сборки-владельцы: %s" % (", ".join(par) if par else "нет"))
        out.append("механизм: file:rename onlysession:true -> file:save (дисковый rename в CREOSON падает General Error)")
        out.append("Выполнить: rename_model old_name=%s new_name=%s dry_run=0" % (old_b, new_b))
        return "\n".join(out)
    before = set(_session())
    log = []
    opened = []
    first = old_b + ext
    if not _open(first):
        return "не открылась модель %s (проверьте имя и рабочую папку %s)" % (first, wd)
    opened.append(first)
    if draw:
        if _open(old_b + ".drw"):
            opened.append(old_b + ".drw")
        else:
            log.append("чертёж %s.drw не открылся — модель переименую без него" % old_b)
            draw = False
    live_par = []
    for p in par:
        if _open(p + ".asm"):
            live_par.append(p)
            opened.append(p + ".asm")
        else:
            log.append("сборка-владелец %s.asm не открылась (пропущена)" % p)
    okr, msg = _rename_session(first, new_b)
    if not okr:
        for f in opened:
            _erase(f)
        return "переименование %s не удалось: %s" % (first, msg)
    log.append("сессионно переименовано: %s -> %s%s" % (old_b, new_b, ext))
    if draw:
        okd, msgd = _rename_session(old_b + ".drw", new_b)
        log.append("чертёж: %s" % ("переименован в %s.drw" % new_b if okd else "ошибка " + msgd))
        if okd:
            cc("drawing", "regenerate", {"drawing": new_b + ".drw"}, 30)
    if not _save(new_b + ext):
        log.append("модель %s%s не сохранилась" % (new_b, ext))
    for p in live_par:
        if not _save(p + ".asm"):
            log.append("сборка-владелец %s.asm не сохранилась" % p)
    if draw and not _save(new_b + ".drw"):
        log.append("чертёж %s.drw не сохранился" % new_b)
    for f in opened:
        _erase(f)
    stamp, moved = _park_old_versions(wd, old_b, log)
    left = sorted(set(_session()) - before)
    return "\n".join([
        "ПЕРЕИМЕНОВАНО %s -> %s (%s); чертёж: %s; сборок-владельцев сохранено: %d" % (
            old_b, new_b, ext, "да" if draw else "нет", len(live_par)),
        "старых версий уведено в backup: %d -> %s" % (moved, stamp),
        "в сессии осталось лишнее: %s" % (", ".join(left) if left else "нет"),
    ] + log)


def tool_preview(old="", new="", drawings=1, **kw):
    plan = build_plan(old, new, drawings)
    if "error" in plan:
        return plan["error"]
    lines = ["План %s -> %s (папка %s)" % (_base(old), _base(new), plan["wd"])]
    lines += ["- %s -> %s (%s)" % (r["old"], r["new"], r["kind"]) for r in plan["rows"]]
    lines.append("сборки-владельцы: %s" % (", ".join(plan["parents"]) if plan["parents"] else "в базе usage не найдены"))
    lines.append("в сессии сейчас моделей: %d" % len(plan["session"]))
    return "\n".join(lines)


TOOLS = [
    {"name": "rename_model", "desc": "Переименовать модель и её чертёж (сессионно + save), старые версии — в backup. dry_run=1 — только план", "params": {"old_name": "старое имя", "new_name": "новое имя", "drawings": "1 переименовать чертёж", "parents": "1 сохранить сборки-владельцы", "dry_run": "1 план / 0 выполнить"}, "approval": True, "fn": tool_rename_model},
    {"name": "rename_preview", "desc": "План переименования модели и чертежа (только чтение)", "params": {"old": "старое имя", "new": "новое имя", "drawings": "1 с чертежом"}, "approval": False, "fn": tool_preview},
]
    if not ext:
        return {"error": "в %s нет файлов %s (prt/asm)" % (wd, old_b)}
    conflict = []
    for e in (ext, ".drw"):
        if list(Path(wd).glob(new_b + e + ".*")):
            conflict.append(new_b + e)
    rows = [{"old": old_b + ext, "new": new_b + ext, "kind": "модель"}]
    if str(drawings) in ("1", "true", "да") and _latest(wd, old_b, ".drw"):
        rows.append({"old": old_b + ".drw", "new": new_b + ".drw", "kind": "чертёж"})
    parents = _parents(wd, old_b)
    return {
        "wd": wd,
        "ext": ext,
        "rows": rows,
        "parents": parents,
        "conflict": conflict,
        "total": len(rows),
        "session": _session(),
    }