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

def brute_force_probe(file_path, target_keys):
    print(f"--- BRUTE FORCE PROBE: {os.path.basename(file_path)} ---")
    try:
        data = read(file_path)
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    for key in target_keys:
        key_bytes = key.encode('latin-1')
        print(f"\n>>> SEARCHING FOR: '{key}' ({key_bytes.hex(' ')})")
        
        # Search for the bytes directly in the data
        indices = [m.start() for m in re.finditer(re.escape(key_bytes), data)]
        
        if not indices:
            print(f"  [!] Key '{key}' not found in binary data.")
            continue
            
        print(f"  [+] Found {len(indices)} occurrences.")
        
        for i, idx in enumerate(indices):
            print(f"\n  --- Occurrence #{i+1} at offset {idx} (0x{idx:X}) ---")
            
            # Define window: 32 bytes before, the key itself, and 64 bytes after
            start = max(0, idx - 32)
            end = min(len(data), idx + len(key_bytes) + 64)
            
            window = data[start:end]
            
            # Hex dump
            print(f"  HEX:   {window.hex(' ')}")
            
            # ASCII dump (replace non-printables with '.')
            ascii_view = "".join([chr(b) if 32 <= b <= 126 else '.' for b in window])
            print(f"  ASCII: {ascii_view}")
            
            # Highlight the key in the ASCII view
            key_pos = idx - start
            print(f"  KEY START POS IN WINDOW: {key_pos}")

if __name__ == "__main__":
    target = r"Z:\PTC\Work\001_15 ЦТКД Электон\ЦТКД 738.01.001-01 Фланец\ctkd_738_01_001-01.prt.11"
    keys_to_find = ['setup_id', 'setup_type', 'MFG_WP_MATERIAL', 'operation']
    brute_force_probe(target, keys_to_find)

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

def brute_force_probe(file_path, target_keys):
    print(f"--- BRUTE FORCE PROBE: {os.path.basename(file_path)} ---")
    try:
        data = read(file_path)
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    for key in target_keys:
        key_bytes = key.encode('latin-1')
        print(f"\n>>> SEARCHING FOR: '{key}' ({key_bytes.hex(' ')})")
        
        # Search for the bytes directly in the data
        indices = [m.start() for m in re.finditer(re.escape(key_bytes), data)]
        
        if not indices:
            print(f"  [!] Key '{key}' not found in binary data.")
            continue
            
        print(f"  [+] Found {len(indices)} occurrences.")
        
        for i, idx in enumerate(indices):
            print(f"\n  --- Occurrence #{i+1} at offset {idx} (0x{idx:X}) ---")
            
            # Define window: 32 bytes before, the key itself, and 64 bytes after
            start = max(0, idx - 32)
            end = min(len(data), idx + len(key_bytes) + 64)
            
            window = data[start:end]
            
            # Hex dump
            print(f"  HEX:   {window.hex(' ')}")
            
            # ASCII dump (replace non-printables with '.')
            ascii_view = "".join([chr(b) if 32 <= b <= 126 else '.' for b in window])
            print(f"  ASCII: {ascii_view}")
            
            # Highlight the key in the ASCII view
            key_pos = idx - start
            print(f"  KEY START POS IN WINDOW: {key_pos}")

if __name__ == "__main__":
    target = r"Z:\PTC\Work\001_15 ЦТКД Электон\ЦТКД 738.01.001-01 Фланец\ctkd_738_01_001-01.prt.11"
    keys_to_find = ['setup_id', 'setup_type', 'MFG_WP_MATERIAL', 'operation']
    brute_force_probe(target, keys_to_find)
