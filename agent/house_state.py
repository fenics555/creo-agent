import os
import sys
import subprocess
import glob
import time
from datetime import datetime, timedelta

def get_netstat_status(port):
    try:
        output = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True, text=True)
        return "LISTENING" in output
    except subprocess.CalledProcessError:
        return False

def get_python_processes():
    # Simplified: looking for any python.exe
    try:
        output = subprocess.check_output("tasklist /FI \"IMAGENAME eq python.exe\"", shell=True, text=True)
        if "python.exe" in output:
            return "Running"
        return "None"
    except Exception:
        return "Error"

def get_progress_status():
    statuses = []
    for f in glob.glob(r"D:\AI\repo\PROGRESS_*.md"):
        try:
            with open(f, 'r', encoding='utf-8') as file:
                content = file.read()
                if "STATUS: В РАБОТЕ" in content:
                    statuses.append(f"{os.path.basename(f)}: В РАБОТЕ")
                else:
                    statuses.append(f"{os.path.basename(f)}: OK")
        except Exception as e:
            statuses.append(f"{os.path.basename(f)}: Error ({str(e)})")
    return statuses if statuses else ["None"]

def get_stale_locks():
    locks = glob.glob(r"D:\AI\tools\agent\*.lock")
    if not locks:
        return ["None"]
    return [os.path.basename(l) for l in locks]

def get_old_urns():
    urn_dir = r"D:\AI\log\urn"
    if not os.path.exists(urn_dir):
        return ["Dir not found"]
    
    old_files = []
    now = time.time()
    for f in os.listdir(urn_dir):
        path = os.path.join(urn_dir, f)
        if os.path.isfile(path):
            if now - os.path.getmtime(path) > 86400:
                old_files.append(f)
    return old_files if old_files else ["None"]

def main():
    print(f"{'CHECK':<25} | {'STATUS':<20}")
    print("-" * 48)
    
    # 1. PID vs Port
    # Assuming pidfile is agent.pid in agent directory
    pid_file = r"D:\AI\tools\agent\agent.pid"
    pid_status = "No pidfile"
    if os.path.exists(pid_file):
        with open(pid_file, 'r') as f:
            try:
                pid = int(f.read().strip())
                pid_status = f"PID {pid}"
            except:
                pid_status = "Invalid PID"
    
    port_status = "LISTENING" if get_netstat_status(8765) else "NOT LISTENING"
    print(f"{'Port 8765 (netstat)':<25} | {port_status:<20}")
    print(f"{'PID File Check':<25} | {pid_status:<20}")

    # 2. Python Processes
    print(f"{'Python Processes':<25} | {get_python_processes():<20}")

    # 3. Progress Files
    print(f"{'Active Progress':<25} | {', '.join(get_progress_status()[:1]):<20}")

    # 4. Stale Locks
    print(f"{'Stale Locks':<25} | {', '.join(get_stale_locks()[:1]):<20}")

    # 5. Old Urns
    print(f"{'Old Urns (>24h)':<25} | {len(get_old_urns()):<20}")

if __name__ == "__main__":
    main()
    sys.exit(0)
