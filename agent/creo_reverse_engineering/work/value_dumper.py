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

try:
    from plm_reader.creo_read import read
except ImportError:
    import creo_read
    from creo_read import read

def dump_values_around_keys(file_path, block_key=b'setup_data'):
    print(f"--- [VALUE DUMP] {os.path.basename(file_path)} ---")
    data = read(file_path)
    
    idx = data.find(block_key)
    if idx == -1:
        print(f"[-] {block_key.decode()} not found.")
        return

    print(f"[+] {block_key.decode()} found at 0x{idx:X}")
    
    # We scan a large window
    start = max(0, idx - 100)
    end = min(len(data), idx + 1000)
    window = data[start:end]
    
    # 1. Find all "parameter-like" names in this window
    # A parameter name in this context usually ends with \x00
    # and is preceded by some header bytes like \xe0\x01 or \xe0\x00
    print("\n--- DETECTED PARAMETERS & THEIR VALUES ---")
    
    # This regex looks for [potential header] [name] \x00
    # We'll use a simpler approach: find all \x00 and look backwards
    null_indices = [m.start() for m in re.finditer(rb'\x00', window)]
    
    for i in range(len(null_indices)):
        end_of_name = null_indices[i]
        # Look back up to 40 bytes for the name
        name_start = max(0, end_of_name - 40)
        name_candidate = window[name_start:end_of_name]
        
        # Clean up the name (remove non-printable or header bytes)
        # We want to find the last sequence of printable characters
        printable_match = re.search(rb'[ -~]{3,32}', name_candidate)
        if printable_match:
            name = printable_match.group().decode('latin-1').strip()
            
            # The value starts after the \x00
            value_start = end_of_name + 1
            value_end = min(len(window), end_of_name + 32)
            value_bytes = window[value_start:value_end]
            
            # Try to interpret value
            val_str = ""
            try:
                # Try string
                val_str = value_bytes.decode('latin-1').strip()
                if not val_str or not any(c.isprintable() for c in val_str):
                    val_str = "[Binary]"
            except:
                val_str = "[Binary]"
                
            # Try to interpret as integer
            val_int = None
            if len(value_bytes) >= 4:
                try:
                    val_int = struct.unpack('<I', value_bytes[:4])[0]
                except:
                    pass
            
            print(f"  NAME: '{name:20}' | STR: {val_str:20} | INT: {str(val_int):10}")

if __name__ == "__main__":
    target = r"Z:\PTC\Work\001_15 ЦТКД Электон\ЦТКД 738.01.001-01 Фланец\ctkd_738_01_001-01.prt.11"
    dump_values_around_keys(target)
