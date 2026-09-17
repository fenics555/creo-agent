import os

file_path = r'D:\AI\tools\agent\loop.py'
backup_path = r'D:\AI\tools\agent\data\backup\pre_66b\agent.py'

if not os.path.exists(file_path):
    print(f"Error: {file_path} not found")
    exit(1)

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Extract _stream_post from backup
with open(backup_path, 'r', encoding='utf-8') as f:
    backup_content = f.read()

# Find _stream_post in backup
import re
stream_match = re.search(r'def _stream_post\(.*?\):.*?return r', backup_content, re.DOTALL)
if not stream_match:
    # Try a broader search if the above failed
    stream_match = re.search(r'def _stream_post\(.*?\):.*?return r', backup_content, re.DOTALL)

# Actually, let's just use the lines I read before to be safe
stream_func = """def _stream_post(path, payload, *ar, **kw):
    push = getattr(threading.current_thread(), \"_tokpush\", None)
    if path != \"/api/chat\" or not push or not settings.get(\"stream_tokens\"):
        return _orig_core_post(path, payload, *ar, **kw)
    payload = dict(payload); payload[\"stream\"] = True
    parts = []; state = {\"buf\": \"\", \"mode\": None}; lastj = {}
    thparts = []
    req = _ur.Request(core.OLL + path, data=json.dumps(payload).encode(), headers={\"Content-Type\": \"application/json\"})
    try:
        with _ur.urlopen(req, timeout=600) as resp:
            for line in resp:
                line = line.strip()
                if not line: continue
                try: j = json.loads(line)
                except Exception: continue
                lastj = j
                t = (j.get(\"message\") or {}).get(\"content\") or \"\"
                tth = (j.get(\"message\") or {}).get(\"thinking\") or \"\"
                if tth:
                    thparts.append(tth)
                    _tc = getattr(threading.current_thread(), \"_tokclient\", None)
                    if _tc is not None:
                        LIVE_THINK.setdefault(_tc, []).append(tth)
                if tth and not t:
                    continue
                if t:
                    parts.append(t)
                    if state[\"mode\"] != \"tool\":
                        state[\"buf\"] += t
                    if state[\"mode\"] is None:
                        if len(state[\"buf\"]) >= 8:
                            if state[\"buf\"].lstrip().startswith(\"[TOOL\"):
                                state[\"mode\"] = \"tool\"
                            else:
                                state[\"mode\"] = \"ans\"; push(state[\"buf\"]); state[\"buf\"] = \"\"
                    elif state[\"mode\"] == \"ans\":
                        push(state[\"buf\"]); state[\"buf\"] = \"\"
    except Exception:
        p2 = dict(payload); p2[\"stream\"] = False
        return _orig_core_post(path, p2, *ar, **kw)
    r = {\"message\": {\"content\": \"\".join(parts), \"thinking\": \"\".join(thparts)}}
    for _kk in (\"prompt_eval_count\", \"eval_count\", \"prompt_eval_duration\", \"eval_duration\"):
        if _kk in lastj: r[_kk] = lastj[_kk]
    return r
"""

# 2. Define Imports
imports = """import re
import json
import threading
import datetime
import time
import urllib.request as _ur
import core
import settings
import users
import tools_registry as TR
import vision_tools as VI
from urllib.parse import parse_qs
"""

# 3. Build the new content
# We'll put imports at the top.
# Then we'll put _stream_post after _clean.
# And at the very end, we'll add the core.post registration.

# Find where _clean ends to insert _stream_post
clean_end_idx = content.find('return txt.strip()')
if clean_end_idx != -1:
    insert_pos = content.find('\n', clean_end_idx) + 1
else:
    insert_pos = 0

new_content = imports + "\n" + content[:insert_pos] + "\n\n" + stream_func + "\n" + content[insert_pos:]

# 4. Add the registration at the end
# We need to make sure _orig_core_post is defined.
registration = """
_orig_core_post = core.post
core.post = _stream_post
"""
new_content += registration

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Repair completed!")
print(f"New file length: {len(new_content)}")
