# -*- coding: utf-8 -*-
import io
cp = r"D:\AI\tools\agent\ctl.py"
s = io.open(cp, encoding="utf-8").read()
if 'up("--browser" in a, "--hidden" in a)' in s:
    print("[~] restart уже передаёт hidden")
else:
    s = s.replace('elif "restart" in a: down(); up("--browser" in a)',
                  'elif "restart" in a: down(); up("--browser" in a, "--hidden" in a)')
    print("[+] restart передаёт --hidden")
old_c = "subprocess.Popen('start \"CREOSON\" /D \"%s\" creoson_run.bat' % CREOSON_DIR, shell=True)"
new_c = "subprocess.Popen('cmd /c start \"\" /B /D \"%s\" creoson_run.bat' % CREOSON_DIR, shell=True)"
if new_c in s: print("[~] creoson уже скрыт")
elif old_c in s:
    s = s.replace(old_c, new_c); print("[+] creoson без окна")
else: print("[x] якорь creoson не найден")
io.open(cp, "w", encoding="utf-8").write(s)
io.open(r"D:\AI\tools\agent\AI_RESTART.bat", "w").write(
    "@echo off\npython D:\\AI\\tools\\agent\\ctl.py restart --browser --hidden\n")
print("[+] AI_RESTART.bat теперь скрытый")
print("ГОТОВО: .\\AI_RESTART.bat")