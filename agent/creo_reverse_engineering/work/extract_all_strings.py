import sys
import os
import re

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

def extract_all_strings(file_path, block_key=b'setup_data'):
    print(f"--- [STRING EXTRACTION] {os.path.basename(file_path)} ---")
    data = read(file_path)
    
    idx = data.find(block_key)
    if idx == -1:
        print(f"[-] {block_key.decode()} not found.")
        return

    print(f"[+] {block_key.decode()} found at 0x{idx:X}")
    
    # Scan a generous window around the block
    start = max(0, idx - 200)
    end = min(len(data), idx + 2000)
    window = data[start:end]
    
    # Find all printable sequences [ -~] (space to tilde)
    # We look for sequences of length 4 to 50
    pattern = rb'[ -~]{4,50}'
    matches = re.finditer(pattern, window)
    
    print("\n--- CANDIDATE STRINGS ---")
    found_strings = []
    for m in matches:
        try:
            s = m.group().decode('latin-1').strip()
            # Filter out strings that are just parameter names we already know
            if s and not any(p in s for p in ['setup_type', 'setup_id', 'setup_data', 'appl_id', 'attr']):
                print(f"  '{s}'")
                found_strings.append(s)
        except:
            pass
    
    return found_strings

if __name__ == "__main__":
    target = r"Z:\PTC\Work\001_15 ЦТКД Электон\ЦТКД 738.01.001-01 Фланец\ctkd_738_01_001-01.prt.11"
    extract_all_strings(target)
