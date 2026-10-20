import sys
import os

sys.path.insert(0, 'D:/AI/tools/agent')
sys.path.insert(0, 'D:/AI/tools/agent/creo_reverse_engineering/src')

from plm_reader.creo_read import read
from creo_protocol_decoder import CreoProtocolDecoder

def find_feature_with_value(file_path, target_val):
    data = read(file_path)
    decoder = CreoProtocolDecoder()
    
    # AllFeatur: (27069, 3789)
    off, length = 27069, 3789
    feat_data = data[off:off+length]
    
    print(f"Searching AllFeatur for any field with value {target_val}...")
    
    curr = 0
    while curr < len(feat_data):
        next_e0 = feat_data.find(b'\xe0', curr)
        if next_e0 == -1:
            break
            
        block_start = next_e0
        next_block_e0 = feat_data.find(b'\xe0', block_start + 1)
        if next_block_e0 == -1:
            block_end = len(feat_data)
        else:
            block_end = next_block_e0
            
        block_data = feat_data[block_start:block_end]
        
        # Check if target_val is in this block
        found_in_block = False
        if isinstance(target_val, int):
            # Try 3 and 4 byte little endian
            for b_len in [3, 4]:
                try:
                    if target_val.to_bytes(b_len, 'little') in block_data:
                        found_in_block = True
                        break
                except OverflowError:
                    continue
        
        if found_in_block:
            print(f"\n[MATCH FOUND at block offset {off + block_start}]")
            inner_curr = 0
            while inner_curr < len(block_data):
                val, n_off, v_type, name = decoder.decode_next_value(block_data, inner_curr)
                if v_type in ["EOF", "NO_HEADER", "DECODE_FAILED"]:
                    break
                print(f"  {name}: {val} ({v_type})")
                inner_curr = n_off if n_off > inner_curr else inner_curr + 1
        
        curr = block_end

if __name__ == "__main__":
    find_feature_with_value('D:/AI/PROBA/models/00080-03.prt', 9611509)
