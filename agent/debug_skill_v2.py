import os

file_path = r"D:\AI\repo\crash\SKILL_crash_protocol_omission.md"
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

print(f"REPR: {repr(content)}")

# Test executor
print(f"EX_CHECK: {'executor:' in content}")

# Test ОШИБКА
import re
match = re.search(r"^\s*ОШИБКА\s*[(:]", content, re.MULTILINE)
print(f"ERR_CHECK: {match is not None}")
if match:
    print(f"MATCH: {match.group(0)}")
else:
    print("NO MATCH")
