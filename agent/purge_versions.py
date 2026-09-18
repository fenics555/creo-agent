import argparse
import json
import logging
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Константы
DEFAULT_EXTENSIONS = {'.prt', '.asm', '.drw', '.frm', '.lay', '.sec', '.mfg', '.dwg', '.dvg'}
LOG_FILE = "purge.log"

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

class PurgeLock:
    def __init__(self, lock_path: Path):
        self.lock_path = lock_path
        self.pid = os.getpid()

    def acquire(self) -> bool:
        if self.lock_path.exists():
            try:
                with open(self.lock_path, 'r') as f:
                    content = f.read().strip()
                    if content:
                        old_pid = int(content)
                        try:
                            os.kill(old_pid, 0)
                            return False
                        except OSError:
                            self.lock_path.unlink()
                        except ValueError:
                            self.lock_path.unlink()
            except Exception:
                pass
        
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.lock_path, 'w') as f:
                f.write(str(self.pid))
            return True
        except Exception:
            return False

    def release(self):
        if self.lock_path.exists():
            try:
                self.lock_path.unlink()
            except Exception:
                pass

def get_file_info(p: Path):
    name = p.name
    stem = p.stem
    suffix = p.suffix.lower()

    if suffix and suffix[1:].isdigit():
        base_path = p.with_suffix('')
        return base_path, int(suffix[1:]), suffix[0]

    match = re.search(r'([._-])(\d+)$', stem)
    if match:
        delim = match.group(1)
        version = int(match.group(2))
        base_stem = stem[:match.start()]
        base_path = p.with_name(base_stem + suffix)
        return base_path, version, delim

    return p, 0, ""
