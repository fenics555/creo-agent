import sys
import os
import json

# Ensure the src directory is in the path for imports
src_dir = r"D:\AI\tools\agent\creo_reverse_engineering\src"
if src_dir not in sys.path:
    sys.path.append(src_dir)

try:
    from creo_links_new import CreoLinksExtractor
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def run_test(file_path):
    print(f"\n--- Testing: {os.path.basename(file_path)} ---")
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    try:
        extractor = CreoLinksExtractor(file_path)
        result = extractor.extract_all()
        
        print(f"[*] PLM Type: {result.get('plm_type', 'Unknown')}")
        print(f"[*] Extracted {len(result.get('edges', []))} edges.")
        
        # Print edges (first 10)
        edges = result.get('edges', [])
        for i, e in enumerate(edges[:10]):
            print(f"  {e}")
        if len(edges) > 10:
            print(f"  ... and {len(edges) - 10} more.")

        # Print parameters
        params = result.get('parameters', {})
        print(f"[*] Extracted Parameters: {params}")
        
        if params:
            print("[+] SUCCESS: Parameters found!")
        else:
            print("[-] INFO: No parameters found. This might be expected if the marker is missing.")

    except Exception as e:
        print(f"[!] Error during extraction: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Target files found during search
    test_files = [
        r"Z:\PTC\Work\000_51 DF Держатели форм\23-171GR1-META 2кап черновой BDF 5 1_2''\23-171gr1-meta.asm.1",
        r"Z:\PTC\Work\000_51 DF Держатели форм\DF-23-171 2кап черновой BDF 5'1_2\df-23-171-171meta.asm.1",
    ]
    
    for f in test_files:
        run_test(f)
