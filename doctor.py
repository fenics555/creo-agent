# -*- coding: utf-8 -*-
from pathlib import Path
AG = Path(r"D:\AI\tools\agent")
ap = AG / "agent.py"; a = ap.read_text(encoding="utf-8")
if "/*lm-deco*/" not in a:
    js = "/*lm-deco*/(function(){var N=['авто','авто+токены','отладка','полный'];function dec(){var b=document.querySelector('[data-v=\"log_mode\"]');if(!b)return;var v=parseInt(b.textContent,10);var w=v+' · '+(N[v]||'');if(b.textContent!=w)b.textContent=w;}document.addEventListener('input',function(e){var t=e.target;if(t&&t.getAttribute&&t.getAttribute('data-cfg')=='log_mode')setTimeout(dec,0);});setInterval(dec,1000);dec();})();"
    a = a.replace("</script>", js + "\n</script>", 1)
    ap.write_text(a, encoding="utf-8"); print("[+] подпись режима логов")
print("ГОТОВО: рестарт + Ctrl+F5")