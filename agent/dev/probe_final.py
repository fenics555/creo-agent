import urllib.request
import json
import threading
import sys
import os
import subprocess

# Add agent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import users
import panel
import draft_tools
import core

def test_final_acceptance():
    print("--- START FINAL ACCEPTANCE PROBE ---")
    host = "http://127.0.0.1:8765"
    
    # 1. Login as admin
    print("Step 1: Logging in as admin...")
    # Using the known admin login/pw from users.json/instructions
    login_data = json.dumps({"login": "admin", "password": "admin"}).encode("utf-8")
    req = urllib.request.Request(host + "/login", data=login_data, headers={"Content-Type": "application/json"})
    
    token = None
    try:
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            if res.get("ok"):
                token = res["token"]
                print(f"SUCCESS: Token obtained: {token}")
            else:
                print(f"FAILED: Login failed: {res}")
    except Exception as e:
        print(f"ERROR: Login request failed: {e}")

    if not token:
        print("CRITICAL: Cannot proceed without admin token.")
        return

    # 2. Check /panel for "📝 Черновики скиллов"
    print("\nStep 2: Checking /panel for '📝 Черновики скиллов'...")
    req_panel = urllib.request.Request(host + "/panel", headers={"X-Token": token})
    try:
        with urllib.request.urlopen(req_panel) as resp:
            res_panel = json.loads(resp.read().decode("utf-8"))
            found = False
            for g in res_panel.get("groups", []):
                title = g.get("title", "")
                if "📝 Черновики скиллов" in title:
                    print(f"FOUND: {title}")
                    found = True
                    break
            if found:
                print("PASSED: Space found in panel.")
            else:
                print("FAILED: Space not found in panel.")
                print(f"Available groups: {[g.get('title') for g in res_panel.get('groups', [])]}")
    except Exception as e:
        print(f"ERROR: /panel request failed: {e}")

    # 3. Direct call drafts_list (testing the tool logic)
    print("\nStep 3: Calling draft_tools.tool_drafts_list()...")
    try:
        res_drafts = draft_tools.tool_drafts_list()
        print(f"Result: {res_drafts}")
        if res_drafts:
            print("PASSED: Got response from tool.")
        else:
            print("INFO: Tool returned empty/None (likely no drafts).")
    except Exception as e:
        print(f"ERROR: Direct tool call failed: {e}")

    # 4. UI Check
    print("\nStep 4: Running ui_check.py...")
    try:
        ui_check_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dev", "ui_check.py"))
        result = subprocess.run(["python", "-X", "utf8", ui_check_path], capture_output=True, text=True)
        print(f"UI Check output:\n{result.stdout}")
        if "ALL GREEN" in result.stdout:
            print("PASSED: UI Check is GREEN.")
        else:
            print("FAILED: UI Check is NOT GREEN.")
    except Exception as e:
        print(f"ERROR: Running ui_check.py failed: {e}")

    print("\n--- END FINAL ACCEPTANCE PROBE ---")

if __name__ == "__main__":
    test_final_acceptance()
