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
    import creo_read
    from creo_read import parse_toc, read
    print("Successfully imported from plm_reader directly.")
except ImportError:
    try:
        from plm_reader import creo_read
        from plm_reader.creo_read import parse_toc, read
        print("Successfully imported from plm_reader package.")
    except ImportError as e:
        print(f"Import Error: {e}")
        sys.exit(1)

def safe_print(s):
    """Print string safely, replacing unencodable characters."""
    try:
        print(s)
    except UnicodeEncodeError:
        print(s.encode('ascii', 'replace').decode('ascii'))

def find_parameter_value(data, toc, target_param_name):
    """
    Searches for a parameter value given its name in the TOC.
    Assumes parameters are in a section that contains the name.
    """
    print(f"\n[Search] Looking for parameter: '{target_param_name}'")
    
    # First, try to find the section that contains the parameter name
    for section_name, (off, length) in toc.items():
        section_data = data[off : off + length]
        # Search for the null-terminated name in this section
        pattern = rb'\x00' + target_param_name.encode('latin-1') + rb'\x00'
        if re.search(pattern, section_data):
            print(f"  -> Found '{target_param_name}' in section '{section_name}'")
            
            # Now we need to find the value. 
            # In Creo, a parameter block is often: [name]\0[value_type]\0[value_data]
            # or similar. Since we don't have the full decoder here, 
            # we'll look for the name and then scan the following bytes for something that looks like a string or number.
            
            match = re.search(pattern, section_data)
            if match:
                start_of_value = match.end()
                # Let's peek at the next 128 bytes to see what's there
                peek_data = section_data[start_of_value : start_of_value + 128]
                
                # Try to find the next null-terminated string or the end of the block
                # This is a heuristic approach.
                val_match = re.search(rb'\x00([^\\x00]{2,64})\x00', peek_data)
                if val_match:
                    return val_match.group(1).decode('latin-1').strip()
                else:
                    # If no null-terminated string, it might be a binary number.
                    # Let's just return the raw bytes for inspection.
                    return f"RAW_BYTES: {peek_data.hex()}"
            
    return None

def probe_part_surgical(file_path, target_params):
    print(f"--- Surgical Probe: {file_path} ---")
    
    try:
        data = read(file_path)
        toc = parse_toc(data)
        print(f"TOC loaded. {len(toc)} sections found.")
    except Exception as e:
        print(f"Failed to read file: {e}")
        return

    for param in target_params:
        val = find_parameter_value(data, toc, param)
        if val:
            print(f"  VALUE FOUND: {val}")
        else:
            print(f"  VALUE NOT FOUND")

if __name__ == "__main__":
    target = r"Z:\PTC\Work\001_15 ЦТКД Электон\ЦТКД 738.01.001-01 Фланец\ctkd_738_01_001-01.prt.11"
    # Based on previous scan: 'setup_id', 'MFG_WP_MATERIAL', 'operation'
    targets = ['setup_id', 'MFG_WP_MATERIAL', 'operation', 'workcell']
    probe_part_surgical(target, targets)
