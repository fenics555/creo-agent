import sys
import os
import json

# Add paths to sys.path to match creo_links_new.py
sys.path.append(r'D:\AI\tools\agent')
sys.path.append(r'D:\AI\tools\agent\creo_reverse_engineering\src')

from creo_links_new import CreoLinksExtractor

def run_validation(file_paths, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    for path in file_paths:
        print(f"\n{'='*80}")
        print(f"VALIDATING: {path}")
        print(f"{'='*80}")
        
        if not os.path.exists(path):
            print(f"[ERROR] File not found: {path}")
            continue
            
        try:
            extractor = CreoLinksExtractor(path)
            edges = extractor.extract_all()
            
            # edges is already a list of dicts because of extract_all() implementation
            edge_dicts = edges
            
            # Create a safe filename
            safe_name = os.path.basename(path).replace(':', '_').replace('/', '_').replace('\\', '_')
            output_file = os.path.join(output_dir, f"edges_{safe_name}.json")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(edge_dicts, f, ensure_ascii=False, indent=2)
                
            print(f"[SUCCESS] Extracted {len(edges)} edges.")
            print(f"[INFO] Results saved to: {output_file}")
            
        except Exception as e:
            print(f"[ERROR] Failed to extract from {path}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    # Files found in Z:\ptc\work\000_51 DF Держатели форм\23-170GR1-META 2кап чистовой BDF 5 1_2''\
    target_files = [
        r"Z:\ptc\work\000_51 DF Держатели форм\23-170GR1-META 2кап чистовой BDF 5 1_2''\23-170gr1-meta-01.prt.1",
        r"Z:\ptc\work\000_51 DF Держатели форм\23-170GR1-META 2кап чистовой BDF 5 1_2''\23-170gr1-meta-02.prt.1"
    ]
    
    output_dir = r"D:\AI\tools\agent\creo_reverse_engineering\validation_results"
    run_validation(target_files, output_dir)
