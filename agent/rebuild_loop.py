import re
import os
import ast

backup_path = r'D:\AI\tools\agent\data\backup\pre_66b\agent.py'
target_path = r'D:\AI\tools\agent\loop.py'

with open(backup_path, 'r', encoding='utf-8') as f:
    content = f.read()

def get_exact_source(tree, content, node):
    start = node.lineno - 1
    end = node.end_lineno
    return "\n".join(content.splitlines()[start:end])

tree = ast.parse(content)

elements = [
    'DEFAULT_PROTO', '_CORE', '_SYS_CACHE', 'PENDING', 'LIVE', 'LAST_META', 'LIVE_TOK', 'LIVE_THINK',
    '_clean', '_stream_post', '_orig_core_post', 'load_skill', '_role_check', 'build_system', 'beh', 
    'parse_model', '_refusal', '_NUDGE', '_ACCESS_NUDGE', 'hist_block', '_two', 'run_loop', 'do_approve'
]

found_elements = []

for node in ast.walk(tree):
    name = None
    if isinstance(node, ast.FunctionDef):
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

registration = "\ncore.post = _stream_post\n"
if "core.post = _stream_post" not in "\n".join(final_parts):
    final_parts.append(registration)

essential_imports = [
    "import re",
    "import json",
    "import threading",
    "import datetime",
    "import time",
    "import urllib.request as _ur",
    "import core",
    "import settings",
    "import users",
    "import tools_registry as TR",
    "import vision_tools as VI",
    "from urllib.parse import parse_qs"
]

final_content = "\n".join(essential_imports) + "\n\n" + "\n\n".join(final_parts)

with open(target_path, 'w', encoding='utf-8') as f:
    f.write(final_content)

print(f"Successfully rebuilt {target_path}")
print(f"Extracted {len(final_parts)} elements.")
