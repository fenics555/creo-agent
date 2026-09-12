# -*- coding: utf-8 -*-
"""АГЕНТ v15 — ЧЕРНОВИКИ СКИЛЛОВ: ночной сборщик и ручное принятие."""
import json, os, datetime
import core

DRAFTS = core.DATA_DIR / "drafts" / "skills"
CHAINS = core.DATA_DIR / "chains.jsonl"


def tool_drafts_build():
    DRAFTS.mkdir(parents=True, exist_ok=True)
    seqs = {}
    if CHAINS.exists():
        lines = CHAINS.read_text(encoding="utf-8", errors="ignore").splitlines()
        print(f"DEBUG: Total lines in CHAINS: {len(lines)}")
        for line in lines:
            if not line.strip(): continue
            try:
                d = json.loads(line)
                print(f"DEBUG: Parsed line: {d}")
                if d.get("ok") and len(d.get("tools") or []) >= 2:
                    key = "->".join(d["tools"][:4])
                    print(f"DEBUG: Match! key: {key}")
                    seqs.setdefault(key, []).append(d)
                else:
                    print(f"DEBUG: No match for line: {d}")
            except Exception as e:
                print(f"DEBUG: Error parsing line: {e}")
    else:
        print("DEBUG: CHAINS does not exist")
    
    print(f"DEBUG: seqs count: {len(seqs)}")
    made = 0
    for key, items in seqs.items():
        print(f"DEBUG: Processing key: {key}, items: {len(items)}")
        if len(items) < 2:
            continue
        fname = DRAFTS / ("chain_%s.md" % key.replace("->", "_")[:60])
        print(f"DEBUG: fname: {fname}")
        if fname.exists():
            print(f"DEBUG: fname exists")
            continue
        body = ["# ЧЕРНОВИК СКИЛЛА: %s" % key, "",
                "Собран ночью из %d успешных цепочек. ТРЕБУЕТ ПРОВЕРКИ ЧЕЛОВЕКОМ." % len(items), ""]
        for d in items[:3]:
            body.append("- Задача: %s" % d.get("q", ""))
            body.append("  Ответ принят: %s" % str(d.get("ok")))
        body += ["", "Принять: drafts_approve name=%s" % fname.name,
                 "Отклонить: drafts_reject name=%s" % fname.name]
        fname.write_text("\n".join(body), encoding="utf-8")
        made += 1
    return "черновиков создано: %d" % made


def tool_drafts_list():
    if not DRAFTS.exists():
        return "черновиков нет"
    ns = [f.name for f in sorted(DRAFTS.glob("*.md"))]
    return "\n".join(ns) or "черновиков нет"


def tool_drafts_approve(name, approval=True):
    src = DRAFTS / name
    if not src.exists():
        return "черновик не найден"
    dst = core.REPO / "Skills" / ("approved_%s" % name)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    src.unlink()
    return "принято в репо: %s" % dst


def tool_drafts_reject(name):
    src = DRAFTS / name
    if src.exists():
        src.unlink()
        return "отклонено и удалено: %s" % name
    return "черновик не найден"


TOOLS = [
    {"name": "drafts_build", "desc": "Собрать черновики скиллов из успешных цепочек (ночная задача)", "params": {}, "fn": tool_drafts_build},
    {"name": "drafts_list", "desc": "Список черновиков скиллов", "params": {}, "fn": tool_drafts_list},
    {"name": "drafts_approve", "desc": "Принять черновик в репо Skills (пишущая)", "params": {"name": "имя файла"}, "approval": True, "fn": tool_drafts_approve},
    {"name": "drafts_reject", "desc": "Отклонить и удалить черновик", "params": {"name": "имя файла"}, "fn": tool_drafts_reject},
]
