import os, sys, argparse, shutil, json, time, datetime, re, subprocess
from pathlib import Path

EXTS = {'.prt', '.asm', '.drw', '.frm', '.lay', '.sec'}

class Lock:
    def __init__(self, p): self.p = Path(p)
    def acq(self):
        if self.p.exists():
            try:
                p_s = self.p.read_text().strip()
                if p_s:
                    p = int(p_s)
                    cmd = f'tasklist /FI "PID eq {p}"'
                    output = subprocess.check_output(cmd, shell=True).decode(errors='ignore')
                    if str(p) in output: return False, f"Locked by {p}"
            except: pass
        self.p.write_text(str(os.getpid()))
        return True, None
    def rel(self):
        if self.p.exists():
            try:
                if int(self.p.read_text().strip()) == os.getpid():
                    self.p.unlink()
            except: pass
