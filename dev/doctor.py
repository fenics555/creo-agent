# -*- coding: utf-8 -*-
# DOCTOR v37 — settings.list_ui: срезовая перезапись между маркерами (лечит {"items": null}).
from pathlib import Path
AG = Path(r"D:\AI\tools\agent")
a = (AG / "settings.py").read_text(encoding="utf-8")
I = a.find("def list_ui(")
J = a.find("def model_for(")
if I < 0 or J < 0 or J < I:
    print("[FAIL] маркеры не найдены"); raise SystemExit(1)
CLEAN = '''def list_ui():
    d = _raw()
    B = {"log_mode": (0, 3, 1), "night_hour": (0, 23, 1), "night_minute": (0, 59, 1),
         "creativity": (0, 100, 1), "auto_temperature": (0, 100, 1), "top_p": (0, 1, 0.05),
         "num_ctx": (1024, 131072, 1024), "num_predict": (256, 8192, 256),
         "log_days": (1, 365, 1), "image_days": (1, 60, 1), "history_days": (1, 365, 1),
         "client_days": (1, 365, 1), "top_chunks": (1, 12, 1), "chunk_chars": (200, 2000, 100),
         "chunk_size": (500, 4000, 250), "chunk_overlap": (0, 1000, 50),
         "repo_boost": (0.5, 3, 0.1), "repo_boost_min_sim": (0, 1, 0.05),
         "vision_gpu": (0, 64, 1), "max_file_mb": (1, 100, 1), "retention": (1, 30, 1),
         "audit_limit": (1, 100, 1), "steps_max": (1, 16, 1), "think_mode": (0, 2, 1),
         "web_quick_links": (0, 100, 1), "web_deep_pages": (0, 200, 5)}
    out = []
    for space, k, name, typ, defl, desc, ui in REGISTRY:
        if not ui:
            continue
        v = d.get(k, defl)
        e = {"space": space, "key": k, "name": name, "type": typ, "value": v, "desc": desc}
        if typ in ("int", "float") and k in B:
            lo, hi, st = B[k]
            e["min"], e["max"], e["step"] = lo, hi, st
            e["kind"] = "range"
        elif typ == "bool":
            e["kind"] = "check"
        else:
            e["kind"] = "text"
        out.append(e)
    return out


'''
a2 = a[:I] + CLEAN + a[J:]
try:
    compile(a2, "settings.py", "exec")
except SyntaxError as e:
    print("[FAIL] синтаксис:", e); raise SystemExit(1)
(AG / "settings.py").write_text(a2, encoding="utf-8")
print("[OK] list_ui переписана срезом")
sl = a2[a2.find("def list_ui("):a2.find("def model_for(")]
print("CHECK return out внутри:", "return out" in sl)