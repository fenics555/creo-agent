import re

path = r"D:\AI\tools\agent\plm_reader\plm_reader.py"
output_path = r"D:\AI\tools\agent\plm_reader\extracted_functions.txt"

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

def get_function_content(start_line_idx):
    content = []
    indent_level = 0
    for i in range(start_line_idx, len(lines)):
        line = lines[i]
        stripped = line.lstrip()
        if not stripped:
            content.append(line)
            continue
        
        # Check indentation
        current_indent = len(line) - len(stripped)
        
        if indent_level == 0:
            indent_level = current_indent
        elif current_indent < indent_level:
            # Function ended
            break
        
        content.append(line)
    return "".join(content)

functions_to_extract = [
    ("load_cache", 38),
    ("save_cache", 49),
    ("_active_db_file", 64),
    ("db_conn", 76),
    ("db_summary", 91),
    ("db_total", 107),
    ("_vol_str", 127),
    ("db_facts", 138),
    ("_ver", 218),
    ("_fs_date", 228),
    ("db_rows_map", 236),
    ("db_rows", 282),
    ("db_search_rows", 326),
    ("LOG_DIR_definition", 371),
    ("log_line", 377),
]

with open(output_path, 'w', encoding='utf-8') as f_out:
    for name, line_num in functions_to_extract:
        f_out.write(f"--- {name} ---\n")
        f_out.write(get_function_content(line_num - 1))
        f_out.write("\n\n")
print(f"Done. Results written to {output_path}")

import re

path = r"D:\AI\tools\agent\plm_reader\plm_reader.py"
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

def get_function_content(start_line_idx):
    content = []
    indent_level = 0
    for i in range(start_line_idx, len(lines)):
        line = lines[i]
        stripped = line.lstrip()
        if not stripped:
            content.append(line)
            continue
        
        # Check indentation
        current_indent = len(line) - len(stripped)
        
        if indent_level == 0:
            indent_level = current_indent
        elif current_indent < indent_level:
            # Function ended
            break
        
        content.append(line)
    return "".join(content)

functions_to_extract = [
    ("load_cache", 38),
    ("save_cache", 49),
    ("_active_db_file", 64),
    ("db_conn", 76),
    ("db_summary", 91),
    ("db_total", 107),
    ("_vol_str", 127),
    ("db_facts", 138),
    ("_ver", 218),
    ("_fs_date", 228),
    ("db_rows_map", 236),
    ("db_rows", 282),
    ("db_search_rows", 326),
    ("LOG_DIR_definition", 371),
    ("log_line", 377),
]

for name, line_num in functions_to_extract:
    print(f"--- {name} ---")
    # line_num is 1-based
    print(get_function_content(line_num - 1))
    print("\n")
