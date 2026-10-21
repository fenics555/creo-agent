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
    # Try direct import if PLM_DIR is in sys.path
    import creo_read
    from creo_read import parse_toc, read
    print("Successfully imported from plm_reader directly.")
except ImportError:
    try:
        # Try package import
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

def probe_part(file_path):
    print(f"--- Probing Part: {file_path} ---")
    
    try:
        data = read(file_path)
        toc = parse_toc(data)
        print(f"TOC loaded. {len(toc)} sections found.")
    except Exception as e:
        print(f"Failed to read file: {e}")
        return

    # Keywords to look for
    target_keywords = ['mfg', 'setup', 'workcell', 'machine', 'install', 'oper', 'tok', 'baza', '4x']
    
    print("\n[1] Scanning all null-terminated strings for keywords...")
    
    matches = re.findall(rb'\x00([^\x00]{2,64})\x00', data)
    
    found_anchors = []
    
    for match in matches:
        try:
            s = match.decode('latin-1').strip()
            if any(kw in s.lower() for kw in target_keywords):
                found_anchors.append(s)
        except:
            continue

    if found_anchors:
        print(f"Found {len(found_anchors)} potential anchors:")
        for anchor in sorted(list(set(found_anchors))):
            safe_print(f"  -> {anchor}")
    else:
        print("No obvious keyword anchors found in strings.")

    print("\n[2] Searching for values associated with manufacturing keywords...")
    
    param_section = None
    for key in toc.keys():
        if 'param' in key.lower() or 'mfg' in key.lower():
            param_section = key
            break
    
    if param_section:
        print(f"Found potential parameter section: {param_section}")
        off, length = toc[param_section]
        param_data = data[off : off + length]
        
        param_matches = re.findall(rb'\x00([^\x00]{2,64})\x00', param_data)
        param_anchors = []
        for m in param_matches:
            try:
                s = m.decode('latin-1').strip()
                if any(kw in s.lower() for kw in target_keywords):
                    param_anchors.append(s)
            except: continue
        
        if param_anchors:
            print(f"Found {len(param_anchors)} potential parameters in {param_section}:")
            for p in sorted(list(set(param_anchors))):
                safe_print(f"  -> {p}")
        else:
            print(f"No manufacturing keywords found inside {param_section}.")
    else:
        print("Could not find a specific 'Parameters' section in TOC. Falling back to global string scan.")

if __name__ == "__main__":
    target = r"Z:\PTC\Work\001_15 ЦТКД Электон\ЦТКД 738.01.001-01 Фланец\ctkd_738_01_001-01.prt.11"
    probe_part(target)
