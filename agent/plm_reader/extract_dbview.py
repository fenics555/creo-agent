import re

path = r"D:\AI\tools\agent\plm_reader\plm_reader.py"
output_path = r"D:\AI\tools\agent\plm_reader\full_dbview_code.txt"

def get_function_content(start_line_idx):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    content = []
    indent_level = 0
    for i in range(start_line_idx, len(lines)):
        line = lines[i]
        stripped = line.lstrip()
        if not stripped:
            content.append(line)
            continue
        
        current_indent = len(line) - len(stripped)
        if indent_level == 0:
            indent_level = current_indent
        elif current_indent < indent_level:
            break
        content.append(line)
    return "".join(content)

functions = [
    ("db_rows", 282),
    ("db_search_rows", 326),
    ("load_cache", 38),
    ("save_cache", 49),
    ("_vol_str", 127),
    ("db_facts", 138),
    ("_ver", 218),
    ("_fs_date", 228),
    ("db_rows_map", 236)
]

with open(output_path, 'w', encoding='utf-8') as f_out:
    for name, line_num in functions:
        f_out.write(f"--- {name} ---\n")
        f_out.write(get_function_content(line_num - 1))
        f_out.write("\n\n")
print(f"Done. Written to {output_path}")
