import os, traceback, sys
sys.path.insert(0, r"D:\AI\tools\agent")
os.chdir(r"D:\AI\tools\agent")
import backup_tools
try:
    print(backup_tools.tool_housekeeping())
except Exception:
    traceback.print_exc(file=sys.stdout)