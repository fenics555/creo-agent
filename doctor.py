# -*- coding: utf-8 -*-
import io, re, json
from pathlib import Path
AG = Path(r"D:\AI\tools\agent")

# 1) scan_exclude: маркеры помоек
cfg = AG / "data" / "config.json"
d = json.loads(cfg.read_text(encoding="utf-8")) if cfg.exists() else {}
se = d.get("scan_exclude") or []
marks = ["не пользоваться", "старое", "хуйня", "учеба", "для копирования", "ремонт"]
add = [m for m in marks if m not in [x.lower() for x in se]]
if add:
    se += add
    d["scan_exclude"] = se
    cfg.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[+] config: scan_exclude += %s" % ", ".join(add))
else:
    print("[~] config: маркеры уже в scan_exclude")

# 2) find_tools: адаптивная группировка + limit 50
ft = AG / "find_tools.py"
s = ft.read_text(encoding="utf-8")
NEW = '''def _folderN(path, n):
    parts = [p for p in re.split(r"[\\\\/]", path) if p]
    body = parts[:-1] or ["?"]
    return "\\\\".join(body[:n]) if len(body) >= n else "\\\\".join(body)

def tool_models_find(q="", ext="", limit=50, **kw):
    where, args = _query(q, ext)
    c = core.db()
    rows = c.execute("SELECT name, ext, path FROM models " + where + " ORDER BY path LIMIT 5000", args).fetchall()
    c.close()
    seen = {}
    for n, e, p in rows:
        key = (re.sub(r"\\.\\d+$", "", n), e)
        if key not in seen:
            seen[key] = (key[0], e, p)
    uniq = sorted(seen.values(), key=lambda x: x[2])
    if not uniq:
        return "по '%s' ничего не нашлось (ищу по именам файлов И папок). Попробуй другое слово." % (q or ext)
    folders = {}
    for depth in (2, 1, 3):
        folders = {}
        for b, e, p in uniq:
            k = _folderN(p, depth)
            folders[k] = folders.get(k, 0) + 1
        if 3 <= len(folders) <= 40:
            break
    out = ["'%s': найдено %d моделей в %d папках." % (q or "все", len(uniq), len(folders))]
    out += ["📁 %s — %d" % (f, n) for f, n in sorted(folders.items(), key=lambda x: -x[1])[:12]]
    out.append("файлы:")
    lim = int(limit) or 50
    out += ["- %s (%s) %s" % (b, e, p) for b, e, p in uniq[:lim]]
    if len(uniq) > lim:
        out.append("…и ещё %d. Уточни папку или имя." % (len(uniq) - lim))
    out.append("Дальше просто напиши имя модели или «вот этот» — продолжу работу с ней.")
    return "\\n".join(out)

'''
m = re.search(r"def _folder\(path\):.*?(?=def tool_models_stats)", s, re.S)
if m:
    s = s[:m.start()] + NEW + s[m.end():]
    ft.write_text(s, encoding="utf-8")
    print("[+] find_tools: адаптивная группировка (2→1→3 уровня), limit=50")
else:
    print("[x] find_tools: якорь _folder не найден")

# 3) agent.py: делегированные обработчики ползунков (числа обновляются всегда)
ap = AG / "agent.py"
a = ap.read_text(encoding="utf-8")
FIX = """
(function(){if(window.__slfix)return;window.__slfix=1;
function sync(r){var lab=r.parentNode.querySelector('[data-v]')||r.nextElementSibling;if(lab)lab.textContent=r.value;}
document.addEventListener('input',function(e){var r=e.target;if(r&&r.type=='range'&&r.getAttribute('data-cfg'))sync(r);});
document.addEventListener('change',function(e){var r=e.target;if(r&&r.type=='range'&&r.getAttribute('data-cfg')){fetch('/setcfg',{method:'POST',headers:{'Content-Type':'application/json','X-Token':window.TK||''},body:JSON.stringify({key:r.getAttribute('data-cfg'),value:r.value})});}});
var mo=new MutationObserver(function(){document.querySelectorAll('input[type=range][data-cfg]').forEach(function(r){var want=parseFloat(r.getAttribute('data-val')||r.value);if(!isNaN(want)){if(parseFloat(r.max)<want)r.max=want;r.value=want;sync(r);}});});
mo.observe(document.body,{childList:true,subtree:true});})();
"""
if "__slfix" not in a and "</script>" in a:
    i = a.rfind("</script>")
    a = a[:i] + FIX + a[i:]
    ap.write_text(a, encoding="utf-8")
    print("[+] agent: ползунки — метка и /setcfg обновляются делегированно")
else:
    print("[~] agent: фикс ползунков уже стоит")
print("ГОТОВО: .\\AI_RESTART.bat, затем index_run (перескан с новыми исключениями)")