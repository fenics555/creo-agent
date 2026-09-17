import re

path_agent = r"D:\AI\tools\agent\agent.py"
path_loop = r"D:\AI\tools\agent\loop.py"

with open(path_agent, "r", encoding="utf-8") as f:
    lines = f.readlines()

# We will build the loop.py content
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
    "\n",
    "# --- Extracted from agent.py ---\n"
]

# Helper to extract a function block
def extract_function(start_line_idx):
    func_lines = []
    found = False
    for i in range(start_line_idx, len(lines)):
        line = lines[i]
        if not found:
            if line.strip().startswith("def "):
                found = True
        
        if found:
            func_lines.append(line)
            # If we are not at the start of the function, check for end of block
            if i > start_line_idx:
                # A function ends when we see a non-indented line that is not empty
                if line.strip() and not line.startswith(" "):
                    break
    return func_lines

# List of functions to extract, in order
functions_to_extract = [
    141, # _role_check
    175, # load_skill
    190, # build_system
    222, # beh
    233, # parse_model
    309, # run_loop
    419, # ask
    541, # do_approve
]

# We also need _clean, _stream_post, _post_before_think, DEFAULT_PROTO
# Let's find them too.
# _clean: 16
# _stream_post: 71
# _post_before_think: 84
# DEFAULT_PROTO: 91

extra_functions = [
    16, # _clean
    71, # _stream_post
    84, # _post_before_think
    91, # DEFAULT_PROTO (this is a variable, not a function)
]

# I'll just manually define the order of extraction
# 1. _clean
# 2. _stream_post
# 3. _post_before_think
# 4. DEFAULT_PROTO
# 5. load_skill
# 6. _role_check
# 7. build_system
# 8. beh
# 9. parse_model
# 10. run_loop
# 11. ask
# 12. do_approve

# Since DEFAULT_PROTO is a variable, I'll handle it specially.

# Let's find the line indices for everything
# _clean: 16
# _stream_post: 71
# _post_before_think: 84
# DEFAULT_PROTO: 91
# load_skill: 175
# _role_check: 141
# build_system: 190
# beh: 222
# parse_model: 233
# run_loop: 309
# ask: 419
# do_approve: 541

# Wait, the order in agent.py is:
# 16: _clean
# 71: _stream_post
# 84: _post_before_think
# 91: DEFAULT_PROTO
# 141: _role_check
# 175: load_skill
# 190: build_system
# 222: beh
# 233: parse_model
# 309: run_loop
# 419: ask
# 541: do_approve

# Let's use this order.

# I will use a list of (start_index, type) where type is 'func' or 'var'
tasks = [
    (16, 'func'), # _clean
    (71, 'func'), # _stream_post
    (84, 'func'), # _post_before_think
    (91, 'var'),  # DEFAULT_PROTO
    (141, 'func'), # _role_check
    (175, 'func'), # load_skill
    (190, 'func'), # build_system
    (222, 'func'), # beh
    (233, 'func'), # parse_model
    (309, 'func'), # run_loop
    (419, 'func'), # ask
    (541, 'func'), # do_approve
]

for idx, task_type in tasks:
    if task_type == 'func':
        func_lines = extract_function(idx)
        new_loop_content.extend(func_lines)
    elif task_type == 'var':
        # For DEFAULT_PROTO, it's a variable. Let's find its end.
        # It seems to be a multiline string.
        # Let's just grab it until the next line that looks like a function or something.
        # Actually, I'll just grab 10 lines.
        for i in range(idx, idx + 10):
            if i < len(lines):
                new_loop_content.append(lines[i])
            else:
                break

with open(path_loop, "w", encoding="utf-8") as f:
    f.writelines(new_loop_content)

print("Rebuilt loop.py successfully.")
