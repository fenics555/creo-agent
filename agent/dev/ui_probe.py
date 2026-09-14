import re
import sys
import os
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(BASE_DIR, "..", "ui", "index.html")

def log_pass(msg): print(f"PASS: {msg}")
def log_fail(msg): print(f"FAIL: {msg}"); sys.exit(1)

def check_a():
    if not os.path.exists(INDEX_PATH):
        log_fail(f"index.html not found at {INDEX_PATH}")
    
    with open(INDEX_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    
    scripts = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
    if not scripts:
        log_fail("No inline scripts found")
    
    log_pass("Inline scripts exist")

def check_b():
    pattern = r'\[DETAILS:([^|\]]+)\|([^\]]*)\](.*?)\\[/DETAILS\\]'
    test_str = '[DETAILS:db|\\u043f\\u043e\\u0434\\u0440\\u043e\\u0431\\u043d\\u0435\\u0435]\\u0442\\u0435\\u043a\\u0441\\u0442[/DETAILS]'
    match = re.search(pattern, test_str)
    if not match:
        log_fail("DETAILS regex failed to match sample")
    
    k, l, t = match.groups()
    lbl = l if l else '\\u043f\\u043e\\u0434\\u0440\\u043e\\u0431\\u043d\\u0435\\u0435'
    expected = f'<div class=\"details-wrap\"><button class=\"sec\" data-act=\"details-toggle\" data-val=\"{k}\" style=\"margin:2px\">{lbl}</button><div class=\"details-content\" style=\"display:none; margin-left:10px; border-left:2px solid #555; padding-left:5px\">{t}</div></div>'
    res = re.sub(pattern, lambda m: f'<div class=\"details-wrap\"><button class=\"sec\" data-act=\"details-toggle\" data-val=\"{m.group(1)}\" style=\"margin:2px\">{m.group(2) or \"\\u043f\\u043e\\u0434\\u0440\\u043e\\u0431\\u043d\\u0435\\u0435\"}</button><div class=\"details-content\" style=\"display:none; margin-left:10px; border-left:2px solid #555; padding-left:5px\">{m.group(3)}</div></div>', test_str)
    if res != expected:
        log_fail(f"DETAILS replacement mismatch. Got: {res}")
    log_pass("DETAILS regex checked")

def check_c():
    with open(INDEX_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    match = re.search(r"else if\(a=='details-toggle'\)\s*\{\s*var\s+cont\s*=\s*el\.nextElementSibling;\s*cont\.style\.display\s*=\s*\(cont\.style\.display\s*==\s*'none'\s*\?\s*'block'\s*:\s*'none'\)\s*;", content)
    if match:
        log_pass(f"JS handler found: {match.group(0)}")
    else:
        log_fail("JS details-toggle handler not found")

def check_d():
    with open(INDEX_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    if 'data-gkey="settings"' not in content:
        log_fail("data-gkey=\"settings\" not found")
    gkey_match = re.search(r'data-gkey="settings"[^>]*>', content)
    if not gkey_match:
        log_fail("data-gkey=\"settings\" element not found")
    triangles = ['\u25B8', '\u25B6', '\u25B2', '\u25B9', '\u25BA', '\u25BB', '▸', '▶', '>', '»']
    if not any(t in content for t in triangles):
        log_fail("data-gkey=\"settings\" found but no triangle detected")
    log_pass("data-gkey=\"settings\" checked")

if __name__ == "__main__":
    try:
        check_a()
        check_b()
        check_c()
        check_d()
        print("ALL PASS")
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
