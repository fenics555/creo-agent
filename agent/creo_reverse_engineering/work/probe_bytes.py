import sys
import os
import re

# Set up paths
ROOT = r'D:\AI\tools\agent'
AGENT_DIR = os.path.join(ROOT, 'creo_reverse_engineering')
SRC_DIR = os.path.join(AGENT_DIR, 'src')
PLM_DIR = os.path.join(ROOT, 'plm_reader')

sys.path.insert(0, ROOT)
sys.path.insert(0, SRC_DIR)
sys.path.insert(0, PLM_DIR)

try:
    from plm_reader.creo_read import parse_toc, read
except ImportError:
    import creo_read
    from creo_read import parse_toc, read

def hex_dump(data, offset, length=64):
    """Print a hex dump of the data."""
    print(f"Hex dump at {offset} (len {length}):")
    chunk = data[offset : offset + length]
    print(f"  HEX: {chunk.hex(' ')}")
    try:
        print(f"  STR: {chunk.decode('latin-1').replace('\\x00', '.')}")
    except:
        print("  STR: (decode error)")

def probe_bytes(file_path, target_str):
    print(f"--- Byte Probe: {file_path} (Target: '{target_str}') ---")
    
    try:
        data = read(file_path)
    except Exception as e:
        print(f"Failed to read file: {e}")
        return

    # Search for the target string surrounded by nulls (as found in previous scan)
    # But let's be more flexible: just find the string itself
    pattern = target_str.encode('latin-1')
    
    matches = list(re.finditer(pattern, data))
    
    if not matches:
        print(f"Target '{target_str}' not found in bytes.")
        return

    print(f"Found {len(matches)} occurrences.")
    
    for i, m in enumerate(matches):
        print(f"\nOccurrence {i+1} at offset {m.start()}:")
        # The name might be preceded by some type/header bytes. 
        # Let's show a bit before and after.
        start_view = max(0, m.start() - 16)
        end_view = min(len(data), m.end() + 48)
        
        print(f"  Context (before/after):")
        hex_dump(data, start_view, end_view - start_view)

if __name__ == "__main__":
    target = r"Z:\PTC\Work\001_15 ЦТКД Электон\ЦТКД 738.01.001-01 Фланец\ctkd_738_01_001-01.prt.11"
    
    # Based on previous scan, let's try 'setup_id'
    probe_bytes(target, "setup_id")
    
    # Also try 'MFG_WP_MATERIAL'
    probe_bytes(target, "MFG_WP_MATERIAL")
