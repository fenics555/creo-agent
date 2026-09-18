import os

content = """# SKILL: crash_protocol_omission

name: crash_protocol_omission
executor: Cline

## Description
Incident: omission of skill writing.

## Prevention
1. Diagnosis
2. Anchor
3. Write skill

ОШИБКА: omission of skill writing
"""

with open(r"D:\AI\repo\crash\SKILL_crash_protocol_omission.md", "w", encoding="utf-8") as f:
    f.write(content)
print("SKILL written successfully")
