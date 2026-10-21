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

class CreoMfgExtractor:
    """
    Specialized extractor for manufacturing-related parameters in Creo files.
    Uses the discovered '\xe0\x01[name]\0' pattern.
    """
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = read(file_path)
        self.toc = parse_toc(self.data)
        self.mfg_params = {}

    def _find_value_after_name(self, data, name_pattern):
        """
        Heuristic: Finds the next null-terminated string or number after a name.
        """
        pattern = rb'\x00' + name_pattern.encode('latin-1') + rb'\x00'
        match = re.search(pattern, data)
        if not match:
            return None
        
        start_of_value = match.end()
        # Peek ahead for the next null-terminated string or a small block of data
        peek_data = data[start_of_value : start_of_value + 128]
        
        # Strategy 1: Look for the next null-terminated string
        val_match = re.search(rb'\x00([^\\x00]{2,64})\x00', peek_data)
        if val_match:
            return val_match.group(1).decode('latin-1').strip()
        
        # Strategy 2: It might be a direct value following the name without another null
        # (e.g. name\0value\0). Let's try to see if the immediate next bytes are printable.
        printable = re.findall(rb'[ -~]{2,32}', peek_data)
        if printable:
            return printable[0].decode('latin-1').strip()

        return None

    def extract_mfg_context(self, target_keys):
        """
        Scans the whole file for specific manufacturing keys.
        """
        print(f"--- Extracting Mfg Context from {os.path.basename(self.file_path)} ---")
        
        for key in target_keys:
            print(f"  Searching for: {key}...")
            val = self._find_value_after_name(self.data, key)
            if val:
                print(f"    [FOUND] {key} = {val}")
                self.mfg_params[key] = val
            else:
                print(f"    [NOT FOUND]")
        
        return self.mfg_params

if __name__ == "__main__":
    # Test with the Flange
    target = r"Z:\PTC\Work\001_15 ЦТКД Электон\ЦТКД 738.01.001-01 Фланец\ctkd_738_01_001-01.prt.11"
    extractor = CreoMfgExtractor(target)
    
    # Targets discovered via Byte Probe
    keys = ['setup_id', 'setup_type', 'MFG_WP_MATERIAL', 'operation']
    results = extractor.extract_mfg_context(keys)
    
    print("\n--- Extraction Summary ---")
    print(results)

import os
import re
import sys

# Path Setup
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

class CreoMfgExtractor:
    """
    Specialized extractor for manufacturing-related parameters in Creo files.
    Uses the discovered '\xe0\x01[name]\0' pattern.
    """
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = read(file_path)
        self.toc = parse_toc(self.data)
        self.mfg_params = {}

    def _find_value_after_name(self, data, name_pattern):
        """
        Heuristic: Finds the next null-terminated string or number after a name.
        """
        pattern = rb'\x00' + name_pattern.encode('latin-1') + rb'\x00'
        match = re.search(pattern, data)
        if not match:
            return None
        
        start_of_value = match.end()
        # Peek ahead for the next null-terminated string
        peek_data = data[start_of_value : start_of_value + 128]
        val_match = re.search(rb'\x00([^\\x00]{2,64})\x00', peek_data)
        
        if val_match:
            return val_match.group(1).decode('latin-1').strip()
        else:
            # If it's not a string, it might be a binary number. 
            # Let's return the hex for debugging.
            return f"HEX:{peek_data[:8].hex()}"

    def extract_mfg_context(self, target_keys):
        """
        Scans the whole file for specific manufacturing keys.
        """
        print(f"--- Extracting Mfg Context from {os.path.basename(self.file_path)} ---")
        
        # We will scan the entire file for the null-terminated pattern 
        # since manufacturing data might be in non-standard sections.
        for key in target_keys:
            print(f"  Searching for: {key}...")
            val = self._find_value_after_name(self.data, key)
            if val:
                print(f"    [FOUND] {key} = {val}")
                self.mfg_params[key] = val
            else:
                print(f"    [NOT FOUND]")
        
        return self.mfg_params

if __name__ == "__main__":
    # Test with the Flange
    target = r"Z:\PTC\Work\001_15 ЦТКД Электон\ЦТКД 738.01.001-01 Фланец\ctkd_738_01_001-01.prt.11"
    extractor = CreoMfgExtractor(target)
    
    # Targets discovered via Byte Probe
    keys = ['setup_id', 'setup_type', 'MFG_WP_MATERIAL', 'operation']
    results = extractor.extract_mfg_context(keys)
    
    print("\n--- Extraction Summary ---")
    print(results)
