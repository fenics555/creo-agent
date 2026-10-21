import os
import struct
import sys

def search_for_int(directory, target_int):
    print(f"Searching for 4-byte integer {target_int} (hex: {hex(target_int)}) in {directory}...")
    found_files = []
    target_bytes = struct.pack('<I', target_int) # Little-endian 4-byte unsigned int
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".prt") or file.endswith(".prt.") or file.endswith(".prt_"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read()
                        if target_bytes in content:
                            print(f"[+] Found in: {file_path}")
                            found_files.append(file_path)
                except Exception:
                    pass
    return found_files

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python search_int.py <directory> <integer>")
        sys.exit(1)
    
    search_dir = sys.argv[1]
    try:
        target_int = int(sys.argv[2])
    except ValueError:
        print("Error: Integer must be a number.")
        sys.exit(1)
    
    results = search_for_int(search_dir, target_int)
    print(f"\nSearch complete. Found {len(results)} files.")
