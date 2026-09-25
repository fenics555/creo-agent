# -*- coding: utf-8 -*-
import os, re

tools = [
    ('cmnm_scan', r'D:\AI\tools\agent\cmnm_scan', 'gui.py'),
    ('config_audit', r'D:\AI\tools\agent\config_audit', 'gui.py'),
    ('copy', r'D:\AI\tools\agent\copy', 'gui.py'),
    ('creo_comb', r'D:\AI\tools\agent\creo_comb', 'gui.py'),
    ('creo_export', r'D:\AI\tools\agent\creo_export', 'gui.py'),
    ('creo_pdf', r'D:\AI\tools\agent\creo_pdf', 'creo_pdf_gui.py'),
    ('skills_check', r'D:\AI\tools\agent\dev', 'skills_check_gui.py'),
    ('dup_scan', r'D:\AI\tools\agent\dup_scan', 'gui.py'),
    ('excel', r'D:\AI\tools\agent\excel', 'gui.py'),
    ('log_clean', r'D:\AI\tools\agent\log_clean', 'gui.py'),
    ('make_lst', r'D:\AI\tools\agent\make_lst', 'gui.py'),
    ('navigator', r'D:\AI\tools\agent\navigator', 'gui.py'),
    ('orphan_scan', r'D:\AI\tools\agent\orphan_scan', 'gui.py'),
    ('purge_versions', r'D:\AI\tools\agent\purge_versions', 'gui.py'),
    ('plm_reader', r'D:\AI\tools\agent\plm_reader', 'plm_reader.py'),
    ('plm_tree', r'D:\AI\tools\agent\plm_tree', 'plm_tree_gui.py'),
]

out = []
for name, p, gui in tools:
    readme = os.path.join(p, 'README.md')
    r_first = open(readme, encoding='utf-8-sig', errors='replace').readline().strip() if os.path.exists(readme) else 'NO README'
    gui_file = os.path.join(p, gui)
    gui_code = open(gui_file, encoding='utf-8', errors='replace').read()
    
    # Check title
    titles = re.findall(r'title\((.*?)\)', gui_code)
    # Check log
    has_log = 'log_line' in gui_code or 'def log' in gui_code or 'LOG' in gui_code
    # Check time
    has_time = 'time.time' in gui_code or 'datetime' in gui_code
    # Check README button
    has_readme_btn = 'README' in gui_code and 'show_readme' in gui_code
    
    out.append(f"=== {name} ===")
    out.append(f"  README: {r_first}")
    out.append(f"  Title: {titles[:2]}")
    out.append(f"  Log: {has_log} | Time: {has_time} | Readme_btn: {has_readme_btn}")

with open(r'D:\AI\tools\agent\audit_tools_canon.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
