# -*- coding: utf-8 -*-
"""АГЕНТ v12 — РЕЕСТР ИНСТРУМЕНТОВ (tools_registry.py)
АВТОПОДКЛЮЧЕНИЕ: каждый файл *_tools.py в папке агента — направление работы.
Блок сам объявляет свой список TOOLS. Реестр только собирает.
Новое направление = новый файл *_tools.py. Больше ничего трогать не надо.
"""
import importlib
from pathlib import Path
from core import log

TOOLS = []
BLOCKS = []
_MODULES = {}          # волна 1: имя блока -> сам модуль (нужно карте инструментов)

def load_all():
    TOOLS[:] = []; BLOCKS[:] = []; _MODULES.clear()
    here = Path(__file__).resolve().parent
    for p in sorted(here.glob("*_tools.py")):
        name = p.stem
        try:
            m = importlib.import_module(name)
            block_tools = getattr(m, "TOOLS", [])
            TOOLS.extend(block_tools)
            BLOCKS.append(name)
            _MODULES[name] = m
            log("реестр: блок <%s> подключён автоматически, инструментов: %d" % (name, len(block_tools)))
        except Exception as e:
            log("реестр: блок <%s> НЕ загружен: %s" % (name, e))

load_all()

import vision_audit
TOOLS.extend(vision_audit.TOOLS)
BLOCKS.append("vision_audit")
_MODULES["vision_audit"] = vision_audit


# --- ВОЛНА 1 (этап 0), 03.10.2026: ТИПЫ ИНСТРУМЕНТОВ -------------------------
# ПОЛЯ в TOOLS необязательные, но реестр УМЕЕТ их читать из самих блоков:
#   {"name":..., "kind":"check", "group":"диагностика", "needs_creo":False, "source":"..."}
# Разметка по умолчанию — по ИМЕНИ БЛОКА (файл *_tools.py), поэтому 46 блоков
# не трогаем. Явное поле в TOOLS всегда побеждает разметку по блоку.
# kind: check | report | act | read | admin | other
KINDS = ("check", "report", "act", "read", "admin", "other")

KIND_BY_BLOCK = {
    # проверки и диагностика
    "diagnostic_tools": "check", "scanner_tools": "check", "study_tools": "check",
    "navigator_tools": "check", "similar_tools": "check", "behavior_tools": "check",
    # отчёты и сводки
    "map_tools": "report", "timeline_tools": "report", "predict_tools": "report",
    # только чтение
    "pdf_tools": "read", "db_tools": "read", "plm_reader_tools": "read",
    "knowledge_tools": "read", "passport_tools": "read", "memory_tools": "read",
    "memory_facts_tools": "read", "trail_tools": "read", "spec_tools": "read",
    "help_tools": "read", "graph_tools": "read", "web_tools": "read",
    "one_c_tools": "read", "nightly_tools": "read",
    # служебное/администрирование
    "git_tools": "admin", "fleet_tools": "admin", "users_tools": "admin",
    "role_tools": "admin", "settings_tools": "admin", "sync_tools": "admin",
    "backup_tools": "admin", "purge_tools": "admin", "prog_tools": "admin",
    "learn_tools": "admin", "diagnostic_admin": "admin",
    # действия (согласования, переименование, копирование, Creo)
    "copy_tools": "act", "rename_tools": "act", "file_hand_tools": "act",
    "draft_tools": "act", "calc_tools": "act", "chat_tools": "act",
    "find_tools": "act", "creo_tools": "act", "creo_ops_tools": "act",
    "creo_pdf_tools": "act", "creo_export_tools": "act", "vision_tools": "act",
    "vision_audit": "act",
}

GROUP_BY_BLOCK = {
    "diagnostic_tools": "диагностика", "scanner_tools": "диагностика",
    "study_tools": "диагностика", "navigator_tools": "диагностика",
    "creo_tools": "Creo", "creo_ops_tools": "Creo", "creo_pdf_tools": "Creo",
    "creo_export_tools": "Creo",
    "pdf_tools": "PDF", "db_tools": "БД", "plm_reader_tools": "PLM",
    "git_tools": "флот", "fleet_tools": "флот", "sync_tools": "флот",
}

# блоки, которым живой Creo обязателен (нужна установка/лицензия)
CREO_BLOCKS = {"creo_tools", "creo_ops_tools", "creo_pdf_tools", "creo_export_tools",
               "creo_comb_tools"}


def meta(t, block=None):
    """Тип инструмента: явное поле TOOLS побеждает разметку по блоку."""
    b = block or ""
    kind = (t.get("kind") or KIND_BY_BLOCK.get(b) or "other").strip().lower()
    return (kind if kind in KINDS else "other",
            (t.get("group") or GROUP_BY_BLOCK.get(b) or b.replace("_tools", "") or "общее"),
            bool(t.get("needs_creo", b in CREO_BLOCKS)),
            t.get("source") or b)


_BY_NAME = {}          # волна 1: имя инструмента -> (kind, group, needs_creo, source)


def meta_of(name):
    """Тип инструмента по ИМЕНИ (блок ищется сам). Нет инструмента = other/''/False/''."""
    return _BY_NAME.get(name, ("other", "", False, ""))


def iter_tools(kind=None, group=None):
    """Инструменты с фильтрами; kind/group задаёт реестр, а не каждый блок."""
    for b in BLOCKS:
        for t in getattr(_MODULES.get(b, object), "TOOLS", []):
            k, g, nc, src = meta(t, b)
            _BY_NAME[t["name"]] = (k, g, nc, src or b)
            if kind and k != kind:
                continue
            if group and g != group:
                continue
            yield k, g, t


def card(kind=None, group=None):
    """Карта инструментов: сводка по kind и group + списки имён."""
    items = list(iter_tools(kind, group))
    lines = ["КАРТА ИНСТРУМЕНТОВ (всего %d%s%s)" % (
        len(items),
        "; kind=%s" % kind if kind else "",
        "; group=%s" % group if group else ""), ""]
    by_kind, by_group = {}, {}
    for k, g, t in items:
        by_kind.setdefault(k, []).append(t["name"])
        by_group.setdefault(g, []).append(t["name"])
    lines.append("— ПО ТИПУ (kind) —")
    for k in KINDS:
        if k in by_kind:
            lines.append("  %-7s %3d : %s" % (k, len(by_kind[k]), ", ".join(sorted(by_kind[k]))))
    lines.append("— ПО ПРЕДМЕТУ (group) —")
    for g in sorted(by_group):
        lines.append("  %-12s %3d : %s" % (g, len(by_group[g]), ", ".join(sorted(by_group[g]))))
    if kind or group:
        lines.append("— ПОЛНЫЕ ОПИСАНИЯ —")
        for k, g, t in items:
            ps = ", ".join((t.get("params") or {}).keys())
            lines.append("- %s(%s) [%s/%s] — %s" % (t["name"], ps, k, g, t.get("desc") or ""))
    return "\n".join(lines)


def get(name):
    for t in TOOLS:
        if t["name"] == name: return t
    return None

def execute(name, args, client=None):
    t = get(name)
    if not t: return "инструмент %s не найден" % name
    if client:
        prof = __import__('users').get_profile(client)
        if prof and __import__('users').role_denied(prof.get("role", "Инженер"), name):
            return "⛔ роль «%s» не может выполнить «%s» (запрет администратора)" % (prof.get("role", "?"), name)
    try:
        return str(t["fn"](**(args or {})))
    except Exception as e:
        log("tool %s err: %s" % (name, e))
        return "ошибка исполнения %s: %s" % (name, e)


def describe():
    out = []
    for t in TOOLS:
        ps = ", ".join(t.get("params", {}).keys()) if t.get("params") else ""
        d = (t.get("desc") or "").strip()
        if len(d) > 45: d = d[:43].rstrip(" ,.;:-") + "…"
        out.append("- %s(%s) — %s%s" % (t["name"], ps, d, " [СОГЛАСОВАНИЕ]" if t.get("approval") else ""))
    return "\n".join(out)
