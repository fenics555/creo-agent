import sys
import os
import struct
import re

# Path Setup
ROOT = r'D:\AI\tools\agent'
AGENT_DIR = os.path.join(ROOT, 'creo_reverse_engineering')
SRC_DIR = os.path.join(AGENT_DIR, 'src')
PLM_DIR = os.path.join(ROOT, 'plm_reader')

sys.path.insert(0, ROOT)
sys.path.insert(0, SRC_DIR)
sys.path.insert(0, PLM_DIR)

# Force UTF-8 for output to avoid UnicodeEncodeError
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

try:
    from plm_reader.creo_read import read
except ImportError:
    import creo_read
    from creo_read import read

def navigate_creo_graph(file_path):
    print(f"--- [GRAPH NAVIGATION] {os.path.basename(file_path)} ---")
    data = read(file_path)
    
    # 1. Find all setup_data sub-blocks
    # They look like 'setup_data(da_setup_...) '
    pattern = rb'setup_data\('
    matches = list(re.finditer(pattern, data))
    
    if not matches:
        print("[-] No setup_data blocks found.")
        return

    print(f"[+] Found {len(matches)} potential setup_data nodes.\n")

    for i, match in enumerate(matches):
        start_idx = match.start()
        print(f"--- NODE #{i} (at 0x{start_idx:X}) ---")
        
        # Define a scan window for this node (e.g., 500 bytes)
        end_idx = min(len(data), start_idx + 500)
        window = data[start_idx:end_idx]
        
        # 2. Within this node, extract all "meaningful" entities
        # Strings
        print("  [Strings]")
        string_pattern = rb'[ -~]{3,32}'
        for sm in re.finditer(string_pattern, window):
            try:
                s = sm.group().decode('latin-1').strip()
                # Filter out things that are likely just the names we already know
                if s and s not in ['setup_data', 'setup_id', 'setup_type']:
                    print(f"    '{s}'")
            except:
                pass
        
        # Integers (4-byte, little-endian)
        print("\n  [Integers]")
        found_ints = []
        for j in range(0, len(window) - 4, 4):
            chunk = window[j:j+4]
            val = struct.unpack('<I', chunk)[0]
            # Filter: common IDs/Offsets (not too huge, not zero)
            if 0 < val < 2000000: # Up to 2MB, reasonable for offsets/IDs
                found_ints.append(val)
            elif val > 10000000: # Likely a larger ID or hash
                found_ints.append(val)
        
        for val in sorted(list(set(found_ints))):
            print(f"    {val}")
        print("\n")

if __name__ == "__main__":
    target = r"Z:\PTC\Work\001_15 ЦТКД Электон\ЦТКД 738.01.001-01 Фланец\ctkd_738_01_001-01.prt.11"
    navigate_creo_graph(target)
