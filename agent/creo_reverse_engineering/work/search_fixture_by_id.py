import sys
import os
import struct

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

def search_files_for_ids(search_dir, target_ids):
    print(f"--- [ID SEARCH] Searching in: {search_dir} ---")
    print(f"--- Targets: {target_ids} ---\n")
    
    found_matches = []
    
    for root, dirs, files in os.walk(search_dir):
        for file in files:
            if file.endswith(('.prt', '.asm', '.drw')):
                full_path = os.path.join(root, file)
                try:
                    # Using the specialized plm_reader to ensure we handle the encoding/reading correctly
                    data = read(full_path)
                    
                    for tid in target_ids:
                        # Check for 4-byte little-endian integer
                        if struct.pack('<I', tid) in data:
                            print(f"[!] MATCH FOUND: {full_path} contains ID {tid}")
                            found_matches.append((full_path, tid))
                            
                except Exception as e:
                    # Silently skip files that can't be read
                    pass
                    
    return found_matches

if __name__ == "__main__":
    # The directory containing all potential fixtures
    SEARCH_DIR = r"Z:\PTC\Work\001_15 ЦТКД Электон\CTKD-PSB Приспособления"
    
    # Candidates from the setup_data analysis
    # 151061240 (id_map_info_ptr)
    # 1601468532 (appears in both nodes)
    # 1812062435 (appears in both nodes)
    # 1970562419 (appears in both nodes)
    CANDIDATE_IDS = [151061240, 1601468532, 1812062435, 1970562419]
    
    results = search_files_for_ids(SEARCH_DIR, CANDIDATE_IDS)
    
    print("\n--- FINAL SEARCH RESULTS ---")
    if results:
        for path, tid in results:
            print(f"ID {tid} -> {path}")
    else:
        print("No matches found. The IDs might be different or I need to search for strings.")
