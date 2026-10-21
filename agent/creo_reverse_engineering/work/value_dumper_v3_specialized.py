import os
import struct
import re

def specialized_dump(file_path):
    print(f"--- [SPECIALIZED DUMP v3] {os.path.basename(file_path)} ---")
    with open(file_path, 'rb') as f:
        data = f.read()

    # 1. Find setup_data block
    setup_idx = data.find(b'setup_data')
    if setup_idx == -1:
        print("[-] setup_data not found")
        return
    print(f"[+] setup_data found at 0x{setup_idx:X}")

    # 2. Find id_map_info_ptr within setup_data
    # We look for the string, then the next null, then the 4-byte value
    ptr_key = b'id_map_info_ptr'
    ptr_idx = data.find(ptr_key, setup_idx)
    if ptr_idx == -1:
        print("[-] id_map_info_ptr not found in setup_data")
        return
    
    print(f"[+] id_map_info_ptr found at 0x{ptr_idx:X}")
    
    # Find the value after the null terminator
    null_idx = data.find(b'\x00', ptr_idx)
    if null_idx == -1:
        print("[-] Null terminator after ptr_key not found")
        return
    
    # The value is 4 bytes after the null
    val_start = null_idx + 1
    val_end = val_start + 4
    val_bytes = data[val_start:val_end]
    
    if len(val_bytes) < 4:
        print("[-] Could not read 4-byte pointer value")
        return

    # Based on our previous discovery, it's little-endian relative offset
    rel_offset = struct.unpack('<I', val_bytes)[0]
    print(f"[+] Relative offset extracted: 0x{rel_offset:X} ({rel_offset})")

    # 3. Jump to the target
    target_idx = setup_idx + rel_offset
    print(f"[+] Jumping to target address: 0x{target_idx:X}")

    if target_idx >= len(data):
        print(f"[-] Target address 0x{target_idx:X} is out of bounds (file size: 0x{len(data):X})")
        return

    # 4. Dump the area
    # We'll dump 1024 bytes around the target
    dump_start = target_idx
    dump_end = min(target_idx + 1024, len(data))
    dump_area = data[dump_start:dump_end]

    print(f"\n--- [MAPPING TABLE DUMP] ---")
    print(f"Start: 0x{dump_start:X}, End: 0x{dump_end:X}")
    print(f"Hex dump (first 256 bytes):")
    print(dump_area[:256].hex(' '))
    
    print(f"\n--- [STRING SCAN IN DUMP AREA] ---")
    # Look for printable strings in the dump area
    # A string is a sequence of printable chars, at least 3 long
    matches = re.finditer(rb'[ -~]{3,50}', dump_area)
    for m in matches:
        try:
            s = m.group().decode('utf-8')
            print(f"  Offset 0x{dump_start + m.start():X}: '{s}'")
        except:
            pass

if __name__ == "__main__":
    target = r"Z:\PTC\Work\001_15 ЦТКД Электон\ЦТКД 738.01.001-01 Фланец\ctkd_738_01_001-01.prt.11"
    specialized_dump(target)
