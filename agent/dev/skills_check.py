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

        # Примечание (аудит 66c, P2/B2): требование «MANIFEST.md reference» снято
        # для экземпляров-прецедентов: прецедент читается как совет, а не закон
        # (конституция, «Маршрут приложений»); закон подключается конституцией.
        # Поэтому бывший пункт «missing MANIFEST.md reference» удалён.

    if not violations:
        print("нарушений: 0")
    else:
        print("нарушения найдены:")
        for v in violations:
            print(f"- {v}")

    # Дельта к снапшоту (аудит 66c, P3/C1): новое нарушение не тонет в фоне.
    try:
        cur = sorted(violations)
        prev = None
        if os.path.exists(BASELINE):
            prev = [l.rstrip("\n") for l in open(BASELINE, encoding="utf-8") if l.strip()]
        if prev is None:
            open(BASELINE, "w", encoding="utf-8").write("\n".join(cur) + "\n")
            print("снапшот создан: %d" % len(cur))
        else:
            new = [v for v in cur if v not in prev]
            fixed = [v for v in prev if v not in cur]
            for v in new:
                print("НОВОЕ: " + v)
            if fixed:
                print("закрыто: %d" % len(fixed))
            if not new and not fixed:
                print("стабильно: %d" % len(cur))
    except Exception as e:
        print("delta err: %r" % e)

if __name__ == "__main__":
    check_crash_skills()
