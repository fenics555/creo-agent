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

class CreoMfgExtractor:
    """
    Ultimate Manufacturing Extractor for Creo.
    Uses direct byte-searching to avoid regex/encoding issues.
    """
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = read(file_path)
        self.mfg_params = {}

    def extract(self, target_keys):
        print(f"--- [ULTIMATE EXTRACTION] {os.path.basename(self.file_path)} ---")
        
        for key in target_keys:
            key_bytes = key.encode('latin-1')
            print(f"  Searching for: '{key}'...")
            
            idx = self.data.find(key_bytes)
            if idx == -1:
                print(f"    [!] NOT FOUND")
                continue
            
            print(f"    [+] FOUND at 0x{idx:X}")
            
            # Define context window around the key
            start = max(0, idx - 40)
            end = min(len(self.data), idx + len(key_bytes) + 80)
            window = self.data[start:end]
            
            # 1. Look for a null-terminated string following the key
            after_key = self.data[idx + len(key_bytes): end]
            
            # Find all nulls in the 'after_key' section
            null_indices = [m.start() for m in re.finditer(rb'\x00', after_key)]
            
            found_val = False
            if len(null_indices) >= 1:
                # Check if there's a string between the first null and a potential second null
                # This is common in Creo parameter blocks
                v_start = null_indices[0] + 1
                if len(null_indices) >= 2:
                    v_end = null_indices[1]
                else:
                    v_end = len(after_key)
                
                if v_end > v_start:
                    try:
                        val = after_key[v_start:v_end].decode('latin-1').strip()
                        if val:
                            print(f"    [VALUE] (String): '{val}'")
                            self.mfg_params[key] = val
                            found_val = True
                    except:
                        pass
            
            if not found_val:
                # 2. Try to find any printable string immediately following the key
                printable_match = re.search(rb'[ -~]{2,64}', after_key)
                if printable_match:
                    try:
                        val = printable_match.group(0).decode('latin-1').strip()
                        if len(val) >= 2:
                            print(f"    [VALUE] (Printable): '{val}'")
                            self.mfg_params[key] = val
                            found_val = True
                    except:
                        pass

            if not found_val:
                # 3. Fallback to Hex
                val_hex = after_key[:8].hex(' ')
                print(f"    [VALUE] (Binary/Hex): {val_hex}")
                self.mfg_params[key] = f"HEX:{val_hex}"

        return self.mfg_params

if __name__ == "__main__":
    target = r"Z:\PTC\Work\001_15 ЦТКД Электон\ЦТКД 738.01.001-01 Фланец\ctkd_738_01_001-01.prt.11"
    keys = ['setup_id', 'setup_type', 'MFG_WP_MATERIAL', 'operation']
    extractor = CreoMfgExtractor(target)
    results = extractor.extract(keys)
    print("\n--- FINAL RESULTS ---")
    print(results)
