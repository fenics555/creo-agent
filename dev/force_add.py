import sys
import os
# Добавляем путь к agent в sys.path, чтобы импортировать users
sys.path.append(r"D:\AI\tools\agent")
import users
import json as _j

print("Attempting to add user...")
_sec = _j.load(open(r"D:\AI\tools\agent\data\secrets.json", encoding="utf-8"))
pw = _sec.get("qa_password", "")
if not pw:
    raise SystemExit("Secrets: qa_password не найден в data\\secrets.json")
success = users.add_user("qa_bot_admin", pw, role="Администратор")
print(f"Success: {success}")

if success:
    print("Checking if user exists in loaded data...")
    print(users.get_profile("qa_bot_admin"))
