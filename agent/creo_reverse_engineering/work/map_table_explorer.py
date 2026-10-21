import os
import struct

def explore_table(file_path):
    print(f"--- [TABLE EXPLORER v1] {os.path.basename(file_path)} ---")
    with open(file_path, 'rb') as f:
        data = f.read()

    setup_idx = data.find(b'setup_data')
    if setup_idx == -1:
        print("[-] setup_data not found")
        return

    ptr_key = b'id_map_info_ptr'
    ptr_idx = data.find(ptr_key, setup_idx)
    if ptr_idx == -1:
        print("[-] id_map_info_ptr not found")
        return

    null_idx = data.find(b'\x00', ptr_idx)
    # The 16-bit offset is at null_idx + 1
    rel_offset = struct.unpack('<H', data[null_idx+1 : null_idx+3])[0]
    print(f"[+] Extracted 16-bit offset: 0x{rel_offset:X} ({rel_offset})")

    table_start = setup_idx + rel_offset
    print(f"[+] Table starts at: 0x{table_start:X}")

    # Let's look at the first 1024 bytes of the table
    table_area = data[table_start : table_start + 1024]
    
    print("\n--- [HEX DUMP OF TABLE START] ---")
    print(table_area[:128].hex(' '))

    print("\n--- [STRING SCAN IN TABLE] ---")
    import re
    # Search for sequences of printable characters
    matches = list(re.finditer(rb'[ -~]{3,30}', table_area))
    for m in matches:
        try:
            s = m.group().decode('utf-8')
            abs_offset = table_start + m.start()
            print(f"  Offset 0x{abs_offset:X}: '{s}'")
        except:
            pass

    print("\n--- [NEARBY STRINGS TO TARGET] ---")
    # We know 10X1-D12 is at 829379. Let's look around it.
    target_offset = 829379
    search_start = max(0, target_offset - 256)
    search_end = min(len(data), target_offset + 256)
    area = data[search_start:search_end]
    
    matches = list(re.finditer(rb'[ -~]{3,30}', area))
    for m in matches:
        try:
            s = m.group().decode('utf-8')
            abs_offset = search_start + m.start()
            print(f"  Offset 0x{abs_offset:X}: '{s}'")
        except:
            pass

if __name__ == "__main__":
    target = r"Z:\PTC\Work\001_15 ЦТКД Электон\ЦТКД 738.01.001-01 Фланец\ctkd_738_01_001-01.prt.11"
    explore_table(target)
