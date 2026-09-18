import os
import re

crash_dir = r"D:\AI\repo\crash"
files = [f for f in os.listdir(crash_dir) if f.endswith(".md")]

print(f"Files in {crash_dir}: {files}")

violations = []
for filename in files:
    file_path = os.path.join(crash_dir, filename)
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "executor:" not in content:
        violations.append(f"{filename}: missing executor field")
    
    if not re.search(r"^\s*ОШИБКА\s*[(:]", content, re.MULTILINE):
        violations.append(f"{filename}: missing ОШИБКА (grep field)")

print(f"Violations count: {len(violations)}")
for v in violations:
    print(f"- {v}")
