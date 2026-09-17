import re
import os
import ast

backup_path = r'D:\AI\tools\agent\data\backup\pre_66b\agent.py'
target_path = r'D:\AI\tools\agent\http_handlers.py'

with open(backup_path, 'r', encoding='utf-8') as f:
    content = f.read()

def get_exact_source(tree, content, node):
    start = node.lineno - 1
    end = node.end_lineno
    return "\n".join(content.splitlines()[start:end])

tree = ast.parse(content)

def find_lines(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node.lineno, node.end_lineno
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return node.lineno, node.end_lineno
    return None, None

# We want the class Hd and do_approve
elements = ['Hd', 'do_approve']

found_elements = []

for node in ast.walk(tree):
    name = None
    if isinstance(node, ast.ClassDef):
        name = node.name
    elif isinstance(node, ast.FunctionDef):
        name = node.name
    elif isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                name = target.id
    
    if name in elements:
        found_elements.append((node.lineno, get_exact_source(tree, content, node), name))

found_elements.sort()

final_parts = []
seen_names = set()
for lineno, source, name in found_elements:
    if name not in seen_names:
        final_parts.append(source)
        seen_names.add(name)

# Essential imports for the handlers
essential_imports = [
    "import json",
    "import re",
    "import os",
    "import socket",
    "import threading",
    "import time",
    "import datetime",
    "from urllib.parse import urlparse, parse_qs",
    "from http.server import BaseHTTPRequestHandler",
    "import core",
    "import settings",
    "import users",
    "import pdf_tools",
    "import tools_registry as TR",
    "import vision_tools as VI",
    "import panel",
    "import queue",
    "from loop import PENDING, LIVE, LAST_META, _wd_port, HOSTNAME, _SYS_CACHE",
    "from loop import do_approve"
]

final_content = "\n".join(essential_imports) + "\n\n" + "\n\n".join(final_parts)

with open(target_path, 'w', encoding='utf-8') as f:
    f.write(final_content)

print(f"Successfully rebuilt {target_path}")
print(f"Extracted {len(final_parts)} elements.")

