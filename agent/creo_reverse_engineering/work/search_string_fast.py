import os
import sys

def search_in_directory(directory, pattern):
    print(f"Searching for '{pattern}' in {directory}...")
    found_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            # More inclusive for Creo files (e.g., .prt.1, .prt.2, .prt_...)
            if "prt" in file.lower():
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read()
                        if pattern.encode('utf-8') in content:
                            print(f"[+] Found in: {file_path}")
                            found_files.append(file_path)
                except Exception as e:
                    pass
    return found_files

if __name__ == "__main__":
    print(f"DEBUG: sys.argv = {sys.argv}")
    if len(sys.argv) < 3:
        print("Usage: python search_script.py <directory> <pattern>")
        sys.exit(1)
    
    search_dir = sys.argv[1]
    search_pattern = sys.argv[2]
    
    results = search_in_directory(search_dir, search_pattern)
    print(f"\nSearch complete. Found {len(results)} files.")
