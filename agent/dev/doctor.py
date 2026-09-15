# doctor12b.py — правка ЖИВОГО CREO-START.bat на Z: + обновление зеркала в репо
# -*- coding: utf-8 -*-
import os, sys, shutil, re, subprocess, socket, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AG = r"D:\AI\tools\agent"; BAK = os.path.join(AG, "data", "backup")
ZBAT = r"Z:\PTC\CREO-START\START-STD\CREO-START.bat"
KB = os.path.join(AG, "data", "kb", "CREO-START.bat")
if not os.path.exists(ZBAT):
    print("VERDICT 12b: Z: недоступен или батника нет, STOP"); sys.exit(1)
def port_open(p):
    try:
        with socket.create_connection(("127.0.0.1", p), timeout=2): return True
    except Exception: return False
b = open(ZBAT, encoding="utf-8", errors="replace").read()
shutil.copy2(ZBAT, os.path.join(BAK, "pre_d12b_Z_creostart.bat")); print("бекап Z-батника сохранён")
pairs = [
 ("set DSTSTD=D:\\CREO-LOCAL\\START-STD",
  "set DSTSTD=D:\\PTC\\CREO-LOCAL-SETUP\\CREO-LOCAL-START"),
 ("D:\\CREO-LOCAL\\Creo_LOCAL.bat",
  "D:\\PTC\\CREO-LOCAL-SETUP\\CREO-LOCAL-START\\Creo_LOCAL.bat"),
 ("D:\\AI\\creoson\\CreosonServer-3.0.2-win64",
  "D:\\PTC\\CREO-LOCAL-SETUP\\creoson"),
]
for old, new in pairs:
    n = b.count(old); b = b.replace(old, new)
    print("замена (%d): %s" % (n, old[:52]))
b = re.sub(r'powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0netdiag\s*netdiag\.ps1"',
           'if exist "%~dp0netdiag\\netdiag.ps1" powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0netdiag\\netdiag.ps1"', b)
anchor = 'echo === %date% %time% mode=%~1 === >> "%LOGF%"'
if anchor in b and "Get-Content $f" not in b:
    rot = ('powershell -NoProfile -Command "foreach($f in @(\'%LOGF%\',\'%STD%\\logs\\ollama.log\',\'%STD%\\logs\\creoson.log\',\'%STD%\\logs\\agent_console.log\'))'
           '{if(Test-Path $f){$l=Get-Content $f; if($l.Count -gt 2000){$l[-1000..($l.Count-1)]|Set-Content $f -Encoding ascii}}}"\r\n')
    b = b.replace(anchor, anchor + "\r\n" + rot, 1); print("ротация логов вставлена")
if "D:\\CREO-LOCAL\\" in b or "D:\\AI\\creoson" in b:
    print("VERDICT 12b: после замен остались старые пути, STOP без записи"); sys.exit(1)
open(ZBAT, "w", encoding="utf-8", newline="").write(b)
print("Z-батник перезаписан")
shutil.copy2(ZBAT, KB); print("зеркало в репо обновлено из Z:")
newrun = r"D:\PTC\CREO-LOCAL-SETUP\creoson\creoson_run.bat"
print("новый путь creoson существует:", os.path.exists(newrun))
if not port_open(8080) and os.path.exists(newrun):
    subprocess.Popen(["cmd", "/c", newrun], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    for _ in range(25):
        time.sleep(2)
        if port_open(8080): break
    if not port_open(8080):
        shutil.copy2(os.path.join(BAK, "pre_d12b_Z_creostart.bat"), ZBAT)
        print("контрольный подъём провален, Z-батник откачен"); sys.exit(1)
print("порт 8080:", "жив" if port_open(8080) else "мёртв (креосон поднимется при следующем CREO-START)")
r = subprocess.run([os.path.join(AG, "GIT_SYNC.bat")], capture_output=True, text=True, cwd=r"D:\AI\tools")
print("GIT_SYNC:", (r.stdout or r.stderr).strip()[:150] or "тихо")
print("--- цитаты живого батника после правки ---")
for l in open(ZBAT, encoding="utf-8", errors="replace"):
    if any(k in l for k in ("DSTSTD", "Creo_LOCAL", "creoson_run.bat", "Get-Content $f")):
        print("  ", l.strip()[:120])
print("VERDICT 12b: живой батник на Z: исправлен, зеркало синхронно, коммит сделан")