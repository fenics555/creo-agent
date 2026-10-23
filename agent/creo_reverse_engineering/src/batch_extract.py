import sys
import os
import json
import traceback
import re

# Add paths to sys.path
sys.path.append(r'D:\AI\tools\agent')
sys.path.append(r'D:\AI\tools\agent\creo_reverse_engineering\src')

from creo_links_new import CreoLinksExtractor

# Use the cleaned list
TARGET_LIST = r"D:\AI\tools\agent\creo_reverse_engineering\target_files_clean.txt"
OUTPUT_DIR = r"D:\AI\tools\agent\creo_reverse_engineering\output\raw_json"

# Only process files that end with these suffixes
RELEVANT_SUFFIXES = ('.asm.1', '.prt.1', '.drw.1', '.tph.1', '.asm', '.prt', '.drw', '.tph')

def batch_run():
    if not os.path.exists(TARGET_LIST):
        print(f"Error: Target list not found at {TARGET_LIST}")
        return

    with open(TARGET_LIST, 'r', encoding='utf-8') as f:
        # Strip whitespace and remove any potential BOM leftovers
        all_files = [line.strip().replace('\ufeff', '') for line in f if line.strip()]

    # Filter for relevant suffixes
    files_to_process = [
        f for f in all_files 
        if f.lower().endswith(RELEVANT_SUFFIXES)
    ]

    print(f"[*] Total files found: {len(all_files)}")
    print(f"[*] Relevant files to process: {len(files_to_process)}")
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    success_count = 0
    error_count = 0

    for i, file_path in enumerate(files_to_process):
        # Use repr() in print to avoid UnicodeEncodeError in terminal
        print(f"[{i+1}/{len(files_to_process)}] Processing: {repr(os.path.basename(file_path))}")
        
        try:
            extractor = CreoLinksExtractor(file_path)
            result = extractor.extract_all()
            
            # Create a safe filename for the JSON
            # Remove any characters that are problematic for filenames
            safe_name = os.path.basename(file_path)
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', safe_name)
            json_filename = f"{safe_name}.json"
            json_path = os.path.join(OUTPUT_DIR, json_filename)
            
            with open(json_path, 'w', encoding='utf-8') as jf:
                json.dump(result, jf, ensure_ascii=False, indent=4)
            
            success_count += 1
            
        except Exception as e:
            print(f"  [!] Failed: {repr(file_path)}")
            print(f"  [!] Error: {e}")
            with open(os.path.join(OUTPUT_DIR, "extraction_errors.log"), "a", encoding="utf-8") as log:
                log.write(f"FILE: {file_path}\nERROR: {str(e)}\n{traceback.format_exc()}\n{'-'*40}\n")
            error_count += 1

    print(f"\n[*] Batch processing complete.")
    print(f"[*] Success: {success_count}")
    print(f"[*] Errors: {error_count}")
    if error_count > 0:
        print(f"[*] Check {os.path.join(OUTPUT_DIR, 'extraction_errors.log')} for details.")

if __name__ == "__main__":
    batch_run()
