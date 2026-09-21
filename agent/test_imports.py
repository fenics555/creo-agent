import os, sys
from pathlib import Path

# Add the agent directory to sys.path
agent_dir = Path(r'D:\AI\tools\agent')
sys.path.append(str(agent_dir))

try:
    import core
    print("core imported successfully")
    from core import log, BASE
    print(f"core.BASE: {BASE}")

    import agent_sched
    print("agent_sched imported successfully")

    import http_handlers
    print("http_handlers imported successfully")

    import settings
    print("settings imported successfully")

    print("All imports successful!")
except Exception as e:
    print(f"Import error: {e}")
    import traceback
    traceback.print_exc()
