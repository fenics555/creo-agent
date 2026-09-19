# -*- coding: utf-8 -*-
"""АГЕНТ v15 — PURGE TOOLS (purge_tools.py)"""
import subprocess
import sys
import json
import os
from pathlib import Path
from core import log

def purge_preview(root, keep):
    """Returns a JSON plan of what will be purged."""
    # Run purge_versions.py with --preview
    # We need to call it via subprocess to avoid issues with current process
    cmd = [sys.executable, "purge_versions.py", "--root", root, "--keep", str(keep), "--preview"]
    try:
        # Assuming output is JSON or we parse it
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if res.stdout.strip():
            return json.loads(res.stdout)
        return {"error": "нет данных для показа"}
    except Exception as e:
        return {"error": str(e)}

def purge_execute(root, keep):
    """Triggers the purge execution."""
    cmd = [sys.executable, "purge_versions.py", "--root", root, "--keep", str(keep), "--execute"]
    try:
        # Detached process
        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        return "Чистка запущена в фоновом режиме."
    except Exception as e:
        return f"Ошибка: {e}"

TOOLS = [
    {
        "name": "purge_preview",
        "desc": "План чистки",
        "params": {"root": "путь", "keep": "число"},
        "fn": purge_preview
    },
    {
        "name": "purge_execute",
        "desc": "Почистить",
        "params": {"root": "путь", "keep": "число"},
        "approval": True,
        "fn": purge_execute
    }
]
