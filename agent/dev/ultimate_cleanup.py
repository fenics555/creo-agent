# -*- coding: utf-8 -*-
import re
from pathlib import Path

def clean_settings():
    path = Path(r"D:\AI\tools\agent\settings.py")
    if not path.exists():
        print(f"Error: {path} not found")
        return
    
    content = path.read_text(encoding="utf-8")
    
    # 1. Fix set_val function
    new_set_val = """def set_val(key, value):
    d = _raw()
    for _, k, typ, _, _, _, _ in REGISTRY:
        if k == key:
            try:
                if typ == "bool": value = str(value).lower() in ("1", "true", "yes", "on", "да")
                elif typ == "int": value = int(value)
                elif typ == "float": value = float(value)
                elif typ == "list" and isinstance(value, str): value = [x.strip() for x in value.split(",") if x.strip()]
            except Exception: pass
            d[key] = value
            if key == "auto_mode" and value is True:
                for _, k2, _, _, defl2, _, _ in REGISTRY:
                    if k2 in ("creativity", "auto_temperature", "top_p", "steps_max"):
                        d[k2] = defl2
            break
    CONFIG_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return True
"""
    lines = content.splitlines()
    start_idx = -1
    end_idx = -1
    for i, line in enumerate(lines):
        if "def set_val(key, value):" in line:
            start_idx = i
        if "return True" in line and i > 110:
            if i + 1 < len(lines) and ("def " in lines[i+1] or lines[i+1].strip() == ""):
                end_idx = i
                break
    
    if start_idx != -1 and end_idx != -1:
        print(f"Replacing set_val from line {start_idx+1} to {end_idx+1}")
        lines[start_idx:end_idx+1] = new_set_val.splitlines()
        content = "\n".join(lines)
    else:
        print("Could not find set_val block to replace.")

    if "}def model_for(role):" in content:
        print("Fixing broken line...")
        content = content.replace("}def model_for(role):", "}\n\ndef model_for(role):")

    path.write_text(content, encoding="utf-8")
    print("settings.py cleaned with ultimate_cleanup.")

def clean_scanner():
    path = Path(r"D:\AI\tools\agent\scanner.py")
    if not path.exists():
        print(f"Error: {path} not found")
        return
    
    content = path.read_text(encoding="utf-8")
    idx = content.find("import sqlite3 as _sq")
    if idx != -1:
        print(f"Found redundant block at index {idx}")
        new_content = content[:idx].rstrip() + "\n"
        path.write_text(new_content, encoding="utf-8")
        print("scanner.py cleaned.")
    else:
        print("No redundant block found in scanner.py.")

if __name__ == "__main__":
    clean_settings()
    clean_scanner()
