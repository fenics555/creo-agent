import os
import re

BASELINE = r"D:\AI\tools\agent\data\skills_check_baseline.txt"

def check_crash_skills():
    crash_dir = r"D:\AI\repo\crash"
    violations = []
    
    if not os.path.exists(crash_dir):
        print(f"Error: {crash_dir} not found")
        return

    files = [f for f in os.listdir(crash_dir) if f.endswith(".md")]
    
    for filename in files:
        file_path = os.path.join(crash_dir, filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # DEBUG PRINT
        print(f"--- DEBUGING {filename} ---")
        print(f"CONTENT: {repr(content)}")

        # 1. name == имя файла без SKILL_ и .md (конституция, БЛОК ИМЁН, ред. 66c)
        name_match = re.search(r'name:\s*([\w-]+)', content)
        if name_match:
            actual_name = name_match.group(1)
            expected_name = filename.replace("SKILL_", "").replace(".md", "")
            if actual_name != expected_name:
                violations.append(f"{filename}: name mismatch (found {actual_name}, expected {expected_name})")
        
        # 2. Skip constitution for other checks
        if filename == "SKILL_crash_constitution.md":
            continue

        # 3. executor обязателен (конституция: поле executor решает закон/совет)
        if "executor:" not in content:
            violations.append(f"{filename}: missing executor field")

        # 4. ОШИБКА-поле обязано быть grep-имым (66c P16): строка начинается
        # с «ОШИБКА», дальше «(» или «:» — оба живых написания принимаются:
        # «ОШИБКА (дословно…» и «ОШИБКА (для grep)».
        if not re.search(r"^\s*ОШИБКА\s*[(:]", content, re.MULTILINE):
            violations.append(f"{filename}: missing ОШИБКА (grep field)")

    if not violations:
        print("нарушений: 0")
    else:
        print("нарушения найдены:")
        for v in violations:
            print(f"- {v}")

if __name__ == "__main__":
    check_crash_skills()
