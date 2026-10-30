import sys
import os
from typing import List, Dict, Any

# Add paths to sys.path
sys.path.append(r'D:\AI\tools\agent')
sys.path.append(r'D:\AI\tools\agent\creo_reverse_engineering\src')

from plm_reader import creo_read
from creo_links import CreoLinksExtractor

def analyze_file(path: str, label: str):
    if not os.path.exists(path):
        print(f"--- {label} NOT FOUND: {path} ---")
        return

    print(f"\n=== ANALYZING {label} ===")
    print(f"Path: {path}")
    
    try:
        extractor = CreoLinksExtractor(path)
        edges = extractor.extract_all()
        
        if not edges:
            print("No edges extracted.")
        else:
            print(f"Extracted {len(edges)} edges:")
            for e in edges:
                print(f"  {e}")
                
        # Additional MdlStatus check
        if "MdlStatus" in extractor.toc:
            print("\n[MdlStatus Attributes]")
            off, ln = extractor.toc["MdlStatus"]
            data = extractor.raw_data[off:off+ln]
            # Quick scan for strings in MdlStatus
            import re
            matches = re.finditer(rb"\x00([^\x00]{2,48})\x00", data)
            for m in matches:
                try:
                    s = m.group(1).decode('latin-1')
                    if s.strip() and not s.startswith('\\x'):
                        print(f"  - {s}")
                except:
                    pass
    except Exception as e:
        print(f"Error analyzing {label}: {e}")

def main():
    project_dir = r"Z:\PTC\Work\001_15 ЦТКД Электон\ЦТКД 738.01.001-01 Фланец"
    
    files_to_analyze = [
        (os.path.join(project_dir, "ctkd_738_01_001-01.asm.48"), "ASSEMBLY (Fixture)"),
        (os.path.join(project_dir, "ctkd_738_01_001-01.prt.11"), "PART (Flange)"),
        (os.path.join(project_dir, "ctkd_738_01_001-01_z.prt.3"), "BLANK/STOCK"),
    ]
    
    for path, label in files_to_analyze:
        analyze_file(path, label)

if __name__ == "__main__":
    main()
