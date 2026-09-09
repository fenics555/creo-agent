import sys
import os
# Добавляем путь к agent в sys.path, чтобы импортировать users
sys.path.append(r"D:\AI\tools\agent")
import users

print("Attempting to add user...")
success = users.add_user("qa_bot_admin", "QaBot2_2026", role="Администратор")
print(f"Success: {success}")

if success:
    print("Checking if user exists in loaded data...")
    print(users.get_profile("qa_bot_admin"))
