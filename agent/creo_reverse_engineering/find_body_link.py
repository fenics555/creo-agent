import sys
import os

sys.path.insert(0, 'D:/AI/tools/agent')
sys.path.insert(0, 'D:/AI/tools/agent/creo_reverse_engineering/src')

from plm_reader.creo_read import read
from creo_protocol_decoder import CreoProtocolDecoder

def dump_block_containing_val(file_path, target_val):
    data = read(file_path)
    decoder = CreoProtocolDecoder()
    
    # AllFeatur: (27069, 3789)
    off, length = 27069, 3789
    feat_data = data[off:off+length]
    
    print(f"Searching AllFeatur for value {target_val}...")
    
    # Search for the bytes
    if isinstance(target_val, int):
        # Try 4 bytes and 3 bytes
        patterns = []
        try: patterns.append(target_val.to_bytes(4, 'little'))
        except: pass
        try: patterns.append(target_val.to_bytes(3, 'little'))
        except: pass
    else:
        patterns = [target_val.encode('utf-8')]
    
    for pattern in patterns:
        idx = feat_data.find(pattern)
        if idx != -1:
            print(f"\n[Found pattern {pattern.hex()} at offset {off + idx}]")
            # Find the block
            # A block starts at the previous e0 and ends at the next e0.
            block_start = feat_data.rfind(b'\xe0', 0, idx)
            if block_start == -1: block_start = 0
            else: block_start += 1
            
            block_end = feat_data.find(b'\xe0', idx)
            if block_end == -1: block_end = len(feat_data)
            
            block_data = feat_data[block_start:block_end]
            
            # Decode the block
            print("  Decoding block contents:")
            inner_curr = 0
            while inner_curr < len(block_data):
                val, n_off, v_type, name = decoder.decode_next_value(block_data, inner_curr)
                if v_type in ["EOF", "NO_HEADER", "DECODE_FAILED"]:
                    break
                print(f"    {name}: {val} ({v_type})")
                inner_curr = n_off if n_off > inner_curr else inner_curr + 1
            return # Found one, stop

if __name__ == "__main__":
    dump_block_containing_val('D:/AI/PROBA/models/00080-03.prt', 9611509)
