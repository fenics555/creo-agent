# -*- coding: utf-8 -*-
import io, re
# 1) usage_tools: срезать РАСШИРЕНИЕ из имён, иначе пересечение всегда пусто
p = r"D:\AI\tools\agent\usage_tools.py"
s = io.open(p, encoding="utf-8").read()
old1 = 'names.add(re.sub(r"\\.\\d+$", "", n).upper())'
new1 = 'names.add(re.sub(r"\\.(prt|asm)(\\.\\d+)?$", "", n).upper())'
if new1 in s: print("[~] usage: расширение уже срезается")
elif old1 in s:
    s = s.replace(old1, new1, 1); io.open(p, "w", encoding="utf-8").write(s)
    print("[+] usage: имена без расширения (пересечение заработает)")
else:
    m = re.search(r"names\.add\(re\.sub\(r\"[^\"]*\", \"\", n\)\.upper\(\)\)", s)
    if m:
        s = s.replace(m.group(0), new1, 1); io.open(p, "w", encoding="utf-8").write(s)
        print("[+] usage: имена без расширения (вариант regex)")
    else:
        print("[x] usage: строка names.add не найдена — покажи кусок build_usage")

# 2) diagnostic_tools: семантический тест known-answer для индекса «где используется»
d = r"D:\AI\tools\agent\diagnostic_tools.py"
t = io.open(d, encoding="utf-8").read()
if "diag_usage" in t:
    print("[~] diag_usage уже есть")
else:
    t += '''

def tool_diag_usage(**kw):
    import core
    c = core.db()
    total = c.execute("SELECT COUNT(*) FROM usage").fetchone()[0]
    known = c.execute("SELECT COUNT(*) FROM usage WHERE child LIKE ? AND parent LIKE ?",
                      ("creoson_tests-01-1%", "creoson_tests-01.%")).fetchone()[0]
    c.close()
    prob = []
    if total == 0: prob.append("индекс пуст: 0 ссылок")
    if known == 0: prob.append("известный ответ не найден: creoson_tests-01-1 в creoson_tests-01")
    v = "ПРОЙДЕН" if not prob else "НЕ ПРОЙДЕН: " + "; ".join(prob)
    return "ссылок: %d, известная пара: %d -> %s" % (total, known, v)

TOOLS.append({"name": "diag_usage", "desc": "Семантический тест индекса «где используется»: ссылок>0 и известная пара на месте", "params": {}, "approval": False, "fn": tool_diag_usage})
'''
    io.open(d, "w", encoding="utf-8").write(t)
    print("[+] diag_usage добавлен")
print("ГОТОВО: .\\AI_RESTART.bat, затем usage_build и diag_usage")