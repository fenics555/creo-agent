import sys
import os
import struct

# Path Setup
ROOT = r'D:\AI\tools\agent'
AGENT_DIR = os.path.join(ROOT, 'creo_reverse_engineering')
SRC_DIR = os.path.join(AGENT_DIR, 'src')
PLM_DIR = os.path.join(ROOT, 'plm_reader')

sys.path.insert(0, ROOT)
sys.path.insert(0, SRC_DIR)
sys.path.insert(0, PLM_DIR)

try:
    from plm_reader.creo_read import read
except ImportError:
    import creo_read
    from creo_read import read

def find_candidates(file_path):
    print(f"--- [CANDIDATE SCAN] {os.path.basename(file_path)} ---")
    data = read(file_path)
    
    # Locate setup_data
    key = b'setup_data'
    idx = data.find(key)
    if idx == -1:
        print("[-] setup_data not found.")
        return

    print(f"[+] setup_data found at 0x{idx:X}")
    
    # Define scan window
    start = max(0, idx - 50)
    end = min(len(data), idx + 500)
    window = data[start:end]
    
    print(f"[*] Scanning window: 0x{start:X} to 0x{end:X}\n")
    
    candidates = {
        "strings": [],
        "integers": []
    }
    
    # 1. Extract Strings
    # We look for sequences of printable characters
    import re
    for match in re.finditer(rb'[ -~]{3,32}', window):
        try:
            s = match.group().decode('latin-1').strip()
            if s:
                candidates["strings"].append(s)
        except:
            pass

    # 2. Extract Integers (4-byte, little-endian)
    for i in range(0, len(window) - 4, 4):
        chunk = window[i:i+4]
        val = struct.unpack('<I', chunk)[0]
        # Filter out obviously non-ID integers (e.g., very small or very large/random looking)
        # But we keep common ones like 1, 5, 738, etc.
        if 0 < val < 1000000:
            candidates["integers"].append(val)

    # Print Results
    print("--- CANDIDATE STRINGS ---")
    for s in sorted(list(set(candidates["strings"]))):
        print(f"  '{s}'")
        
    print("\n--- CANDIDATE INTEGERS ---")
    for v in sorted(list(set(candidates["integers"]))):
        print(f"  {v}")

    return candidates

if __name__ == "__main__":
    target = r"Z:\PTC\Work\001_15 ЦТКД Электон\ЦТКД 738.01.001-01 Фланец\ctkd_738_01_001-01.prt.11"
    find_candidates(target)
