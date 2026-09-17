import re

path_agent = r"D:\AI\tools\agent\agent.py"
path_loop = r"D:\AI\tools\agent\loop.py"

with open(path_agent, "r", encoding="utf-8") as f:
    lines = f.readlines()

def get_func_lines(start_idx):
    func_lines = []
    found = False
    for i in range(start_idx, len(lines)):
        line = lines[i]
        if not found:
            if line.strip().startswith("def "):
                found = True
        if found:
            func_lines.append(line)
            if i > start_idx and line.strip() and not line.startswith(" "):
                break
    return func_lines

# Manually defined start indices for functions in agent.py
# Based on my previous successful reads
# _clean: 16
# _stream_post: 71
# _post_before_think: 84
# DEFAULT_PROTO: 91 (not a func, but a var)
# _role_check: 141
# load_skill: 175
# build_system: 190
# beh: 222
# parse_model: 233
# run_loop: 309
# ask: 419
# do_approve: 541

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

# 1. _clean
new_loop_content.extend(get_func_lines(16))
# 2. _stream_post
new_loop_content.extend(get_func_lines(71))
# 3. _post_before_think
new_loop_content.extend(get_func_lines(84))
# 4. DEFAULT_PROTO
# Let's find DEFAULT_PROTO in agent.py. It's a variable.
for i in range(91, 100):
    if "DEFAULT_PROTO =" in lines[i]:
        new_loop_content.append(lines[i])
        break
new_loop_content.append("\n")
# 5. _role_check
new_loop_content.extend(get_func_lines(141))
# 6. load_skill
new_loop_content.extend(get_func_lines(175))
# 7. build_system
new_loop_content.extend(get_func_lines(190))
# 8. beh
new_loop_content.extend(get_func_lines(222))
# 9. parse_model
new_loop_content.extend(get_func_lines(233))
# 10. run_loop
new_loop_content.extend(get_func_lines(309))
# 11. ask
new_loop_content.extend(get_func_lines(419))
# 12. do_approve
new_loop_content.extend(get_func_lines(541))

with open(path_loop, "w", encoding="utf-8") as f:
    f.writelines(new_loop_content)

print("Rebuilt loop.py from scratch successfully.")
