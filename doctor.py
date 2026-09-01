# -*- coding: utf-8 -*-
import io, re
p = r"D:\AI\tools\agent\usage_tools.py"
s = io.open(p, encoding="utf-8").read()
good_n = 're.sub(r"\\.(prt|asm)(\\.\\d+)?$", "", n).upper()'
good_p = 're.sub(r"\\.(prt|asm)(\\.\\d+)?$", "", os.path.basename(path)).upper()'
if good_n in s and good_p in s:
    print("[~] уже правильно")
else:
    s2 = re.sub(r'names\.add\(re\.sub\(r["\'][^"\']*["\'],\s*"",\s*n\)\.upper\(\)\)',
                lambda m: 'names.add(%s)' % good_n, s)
    s2 = re.sub(r'parent\s*=\s*re\.sub\(r["\'][^"\']*["\'],\s*"",\s*os\.path\.basename\(path\)\)\.upper\(\)',
                lambda m: 'parent = %s' % good_p, s2)
    if s2 == s:
        print("[x] строки names.add/parent не распознаны — покажи кусок build_usage")
    else:
        io.open(p, "w", encoding="utf-8").write(s2)
        print("[+] имена и parent теперь без расширения")
print("ТЕПЕРЬ: .\\AI_RESTART.bat -> usage_build -> ждать -> diag_usage")