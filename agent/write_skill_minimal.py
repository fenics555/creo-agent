import os

content = """name: crash_protocol_omission
executor: Cline
ОШИБКА: error
"""

with open(r"D:\AI\repo\crash\SKILL_crash_protocol_omission.md", "w", encoding="utf-8") as f:
    f.write(content)
print("SKILL written successfully")
