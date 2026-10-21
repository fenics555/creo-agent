import sys
import os

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

def brute_force_probe(file_path, target_keys):
    print(f"--- BRUTE FORCE PROBE: {os.path.basename(file_path)} ---")
    try:
        data = read(file_path)
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    for key in target_keys:
        key_bytes = key.encode('latin-1')
        print(f"\nSearching for key: '{key}' ({key_bytes.hex()})")
        
        indices = [m.start() for m in re.finditer(re.escape(key_bytes).encode('latin-1'), data)]
        
        if not indices:
            print(f"  [!] Key '{key}' NOT FOUND in binary.")
            continue
        
        print(f"  [+] Found {len(indices)} occurrences.")
        
        for i, idx in enumerate(indices):
            print(f"\n  Occurrence #{i+1} at offset {idx} (0x{idx:X}):")
            
            # Context: 32 bytes before, 32 bytes after
            start = max(0, idx - 32)
            end = min(len(data), idx + len(key_bytes) + 32)
            
            context = data[start:end]
            
            print(f"    HEX: {context.hex(' ')}")
            
            # ASCII representation (safe)
            ascii_ctx = "".join([chr(b) if 32 <= b <= 126 else "." for b in context])
            print(f"    ASCII: {ascii_ctx}")

import re
if __name__ == "__main__":
    target = r"Z:\PTC\Work\001_15 ЦТКД Электон\ЦТКД 738.01.001-01 Фланец\ctkd_738_01_001-01.prt.11"
    keys = ['setup_id', 'setup_type', 'MFG_WP_MATERIAL', 'operation']
    brute_force_probe(target, keys)
