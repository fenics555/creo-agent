import re

path_agent = r"D:\AI\tools\agent\agent.py"
path_loop = r"D:\AI\tools\agent\loop.py"

with open(path_agent, "r", encoding="utf-8") as f:
    content = f.read()

# Find all functions and their ranges
# Regex for function definition: ^def name(args):
# We'll use re.MULTILINE
func_pattern = re.compile(r'^def\s+(\w+)\s*\(.*?\):', re.MULTILINE)

functions = {}
for match in func_pattern.finditer(content):
    name = match.group(1)
    start_pos = match.start()
    
    # Find the end of the function by looking for the next non-indented line
    # that is not empty.
    end_pos = len(content)
    
    # Get the text after the start_pos
    after_match = content[start_pos:]
    lines = after_match.splitlines(keepends=True)
    
    # The first line is the def line itself
    for i in range(1, len(lines)):
        if lines[i].strip() and not lines[i].startswith(' '):
            end_pos = start_pos + len("".join(lines[:i]))
            break
    
    functions[name] = (start_pos, end_pos)

print("Found functions:", list(functions.keys()))

# Now we want to extract specific ones
target_names = [
    "_clean",
    "_stream_post",
    "_post_before_think",
    "load_skill",
    "_role_check",
    "build_system",
    "beh",
    "parse_model",
    "run_loop",
    "ask",
    "do_approve"
]

new_loop_content = [
    "import json, re, os, socket, threading, time, datetime\n",
    "from concurrent.futures import ThreadPoolExecutor\n",
    "import subprocess, sys\n",
    "from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler\n",
    "from urllib.parse import urlparse, parse_qs\n",
    "import core\n",
    "from core import log, trace\n",
    "import settings\n",
    "import pdf_tools\n",
    "import urllib.request as _ur\n",
    "import tools_registry as TR\n",
    "import scanner\n",
    "import users\n",
    "import chat_tools\n",
    "import panel\n",
    "import vision_tools as VI\n",
    "import sched\n",
    "\n",
    "LIVE_TOK = {}\n",
    "LIVE_THINK = {}\n",
    "_orig_core_post = core.post\n",
    "\n"
]

# Add DEFAULT_PROTO
# Find DEFAULT_PROTO in content
proto_match = re.search(r'DEFAULT_PROTO = (.*)', content)
if proto_match:
    # Since it might be a multi-line string, let's be careful.
    # But it's likely a docstring.
    # Let's just find the line and take the next few lines until it ends.
    # Actually, in agent.py it is:
    # DEFAULT_PROTO = \"\"\"...\"\"\"
    # Let's use a regex for it.
    proto_match = re.search(r'DEFAULT_PROTO = \"\"\"([\s\S]*?)\"\"\"', content)
    if proto_match:
        new_loop_content.append("DEFAULT_PROTO = \"\"\"\n" + proto_match.group(1) + "\n\"\"\"\n\n")

for name in target_names:
    if name in functions:
        start, end = functions[name]
        new_loop_content.append(content[start:end])
        new_loop_content.append("\n")
    else:
        print(f"Warning: {name} not found!")

with open(path_loop, "w", encoding="utf-8") as f:
    f.writelines(new_loop_content)

print("Rebuilt loop.py using regex extraction successfully.")
