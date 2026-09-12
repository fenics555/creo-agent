import urllib.request
import json
import threading
import sys
import os

# Add agent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import users
import panel
import draft_tools
import core

def test_spec_16_v2():
    print("--- START SPEC 16 V2 PROBE ---")
    
    host = "http://127.0.0.1:8765"
    
    # 1. Login as admin to get token
    print("Step 1: Logging in as admin...")
    login_data = json.dumps({"login": "admin", "password": "admin"}).encode("utf-8")
    req = urllib.request.Request(host + "/login", data=login_data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            if res.get("ok"):
                token = res["token"]
                print(f"SUCCESS: Token obtained: {token}")
            else:
                print(f"FAILED: Login failed: {res}")
                token = None
    except Exception as e:
        print(f"ERROR: Login request failed: {e}")
        token = None

    if token:
        # 2. Call /panel
        print("\nStep 2: Calling /panel...")
        req_panel = urllib.request.Request(host + "/panel", headers={"X-Token": token})
        try:
            with urllib.request.urlopen(req_panel) as resp:
                res_panel = json.loads(resp.read().decode("utf-8"))
                print("Panel groups found:")
                for g in res_panel.get("groups", []):
                    print(f" - {g.get('title')}")
                
                # Check for the specific space
                found_space = False
                for g in res_panel.get("groups", []):
                    if "📝 Черновики скиллов" in g.get("title", ""):
                        print(f"FOUND: {g.get('title')}")
                        found_space = True
                        break
                if not found_space:
                    print("FAILED: Could not find '📝 Черновики скиллов' in panel groups")
                else:
                    print("PASSED: Space found")
        except Exception as e:
            print(f"ERROR: /panel request failed: {e}")

        # 3. Direct call drafts_list
        print("\nStep 3: Direct call drafts_list...")
        try:
            # tool_drafts_list is the function
            res_drafts = draft_tools.tool_drafts_list()
            print(f"Result: {res_drafts}")
            if res_drafts and "черновиков нет" not in res_drafts.lower():
                 print("PASSED: Got drafts list")
            else:
                 print("INFO: Drafts list empty or 'no drafts' (this is okay if no drafts exist)")
        except Exception as e:
            print(f"ERROR: Direct call drafts_list failed: {e}")

    else:
        print("SKIPPING steps 2 and 3 due to login failure.")

    # 4. UI Check
    print("\nStep 4: Running ui_check.py...")
    import subprocess
    try:
        # Use absolute path to be safe
        ui_check_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dev", "ui_check.py"))
        result = subprocess.run(["python", "-X", "utf8", ui_check_path], capture_output=True, text=True)
        print(f"UI Check output:\n{result.stdout}")
        if "ALL GREEN" in result.stdout:
            print("PASSED: UI Check is GREEN")
        else:
            print("FAILED: UI Check is NOT GREEN")
    except Exception as e:
        print(f"ERROR: Running ui_check.py failed: {e}")

    print("\n--- END SPEC 16 V2 PROBE ---")

if __name__ == "__main__":
    test_spec_16_v2()
