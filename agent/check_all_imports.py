import os, re

agent_dir = r'D:\AI\Tools\agent'

# Список всех .py файлов в корне (без подпапок)
root_files = [f for f in os.listdir(agent_dir) if f.endswith('.py')]
root_names = {f[:-3] for f in root_files}

# Файлы, которые НЕ импортируются из корня (из предыдущего анализа)
not_imported_from_root = [
    '_ddl2.py', 'audit_check.py', 'batch_params_tools.py', 'calc_tools.py',
    'clean_skill.py', 'creo_export_tools.py', 'creo_path.py', 'creo_pdf_tools.py',
    'creo_read.py', 'ctl.py', 'drawing_audit_tools.py', 'env_probe.py',
    'harvest_reader.py', 'hol_tools.py', 'house_state.py', 'log_clean.py',
    'navigator_tools.py', 'one_c_tools.py', 'plan_run_tools.py',
    'probe_8080.py', 'probe_tk.py', 'probe_write_shield.py', 'purge_gui.py',
    'purge_versions.py', 'rules_engine.py', 'skills_index_tools.py',
    'tool_contract.py', 'ui_common.py'
]

# 1. Проверяем импорты из ПОДПАПОК
print("=== ПРОВЕРКА ИМПОРТОВ ИЗ ПОДПАПОК ===")
subdir_imports = {}
for subdir in os.listdir(agent_dir):
    subdir_path = os.path.join(agent_dir, subdir)
    if not os.path.isdir(subdir_path):
        continue
    for fname in os.listdir(subdir_path):
        if not fname.endswith('.py'):
            continue
        fpath = os.path.join(subdir_path, fname)
        try:
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except:
            continue
        
        imported_root = set()
        for m in re.finditer(r'^\s*import\s+([\w_]+)', content, re.MULTILINE):
            mod = m.group(1)
            if mod in root_names:
                imported_root.add(mod)
        for m in re.finditer(r'^\s*from\s+([\w_]+)\s+import', content, re.MULTILINE):
            mod = m.group(1)
            if mod in root_names:
                imported_root.add(mod)
        
        for mod in imported_root:
            if mod not in subdir_imports:
                subdir_imports[mod] = []
            subdir_imports[mod].append(f"{subdir}/{fname}")

# 2. Проверяем вызовы из .bat файлов
print("\n=== ПРОВЕРКА ВЫЗОВОВ ИЗ .bat ===")
bat_calls = {}
for fname in os.listdir(agent_dir):
    if not fname.endswith('.bat'):
        continue
    fpath = os.path.join(agent_dir, fname)
    try:
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except:
        continue
    
    # Ищем вызовы python с именами файлов из корня
    for root_name in root_names:
        # ищем "python имя.py" или "имя.py" или "name.py"
        if re.search(r'python\s+\S*' + re.escape(root_name) + r'\.py', content, re.IGNORECASE):
            if root_name not in bat_calls:
                bat_calls[root_name] = []
            bat_calls[root_name].append(fname)
        if re.search(r'\b' + re.escape(root_name) + r'\.py\b', content):
            if root_name not in bat_calls:
                bat_calls[root_name] = []
            if fname not in bat_calls[root_name]:
                bat_calls[root_name].append(fname)

# 3. Итоговый отчет
print("\n=== ИТОГОВЫЙ ОТЧЕТ: Файлы, не импортируемые из корня ===\n")
for fname in sorted(not_imported_from_root):
    mod_name = fname[:-3]
    subdirs = subdir_imports.get(mod_name, [])
    bats = bat_calls.get(mod_name, [])
    
    used = bool(subdirs or bats)
    status = "ИСПОЛЬЗУЕТСЯ" if used else "НЕ ИСПОЛЬЗУЕТСЯ"
    
    print(f"\n{fname} -> {status}")
    if subdirs:
        print(f"  Импортируется из подпапок: {subdirs}")
    if bats:
        print(f"  Вызывается из .bat: {bats}")
    if not subdirs and not bats:
        print(f"  >>> МОЖНО ПЕРЕНОСИТЬ В TEST <<<")

print("\n" + "="*60)
print("ПОДСЧЁТ: Можно перенести в TEST (не используются нигде):")
count = 0
for fname in sorted(not_imported_from_root):
    mod_name = fname[:-3]
    subdirs = subdir_imports.get(mod_name, [])
    bats = bat_calls.get(mod_name, [])
    if not subdirs and not bats:
        count += 1
        print(f"  {fname}")
print(f"\nВсего можно перенести: {count}")