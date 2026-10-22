import os
import struct
import re

def iterate_table(file_path, table_start, limit=2048):
    print(f"--- [TABLE ITERATOR] {os.path.basename(file_path)} ---")
    print(f"Starting at: 0x{table_start:X}, Limit: {limit} bytes")
    
    with open(file_path, 'rb') as f:
        data = f.read()

    end = min(table_start + limit, len(data))
    table_data = data[table_start:end]
    
    print("\n--- [ITERATION RESULTS] ---")
    print(f"{'Offset':<10} | {'Type':<6} | {'Content'}")
    print("-" * 50)

    # We look for markers: e2, e3, f7 or sequences of printable chars
    # A more robust way: find all sequences of printable chars and their markers
    
    cursor = 0
    while cursor < len(table_data):
        # Find the next potential marker or printable string
        # Search for markers: 0xe2, 0xe3, 0xf7
        match = re.search(rb'[\xe2\xe3\xf7]', table_data[cursor:])
        if not match:
            break
        
        # Match position relative to table_start
        match_rel_pos = cursor + match.start()
        abs_pos = table_start + match_rel_pos
        marker = match.group(0)
        
        # After marker, find the string (ends at 00 or f7 or next marker)
        # Look for printable sequence
        remaining = table_data[match_rel_pos + 1:]
        string_match = re.search(rb'[ -~]{2,30}', remaining)
        
        if string_match:
            str_start = match_rel_pos + 1 + string_match.start()
            str_end = match_rel_pos + 1 + string_match.end()
            
            # Check for null terminator or f7 immediately after
            content = string_match.group().decode('latin-1', errors='replace')
            
            print(f"0x{abs_pos:X} | {marker.hex():<6} | '{content}'")
            
            # Move cursor to after the string
            cursor = str_end
        else:
            cursor = match_rel_pos + 1

if __name__ == "__main__":
    target = r"Z:\PTC\Work\001_15 ЦТКД Электон\ЦТКД 738.01.001-01 Фланец\ctkd_738_01_001-01.prt.11"
    table_offset = 0xCA723  # Из предыдущего анализа
    iterate_table(target, table_offset)
