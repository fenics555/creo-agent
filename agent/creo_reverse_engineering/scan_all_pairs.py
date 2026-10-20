import sys
import os

sys.path.append('D:/AI/tools/agent')
sys.path.append('D:/AI/tools/agent/creo_reverse_engineering/src')

from plm_reader.creo_read import read
from creo_protocol_decoder import CreoProtocolDecoder

def scan_all_pairs(file_path):
    data = read(file_path)
    decoder = CreoProtocolDecoder()
    
    # AllFeatur: (27069, 3789)
    off, length = 27069, 3789
    feat_data = data[off:off+length]
    
    print(f"--- Scanning AllFeatur for feat_id and body_id pairs ---")
    
    curr = 0
    while curr < len(feat_data):
        # Find the start of a block (an e0 header)
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
        
        # Inside this block, find all feat_id and body_id
        f_id = None
        b_id = None
        
        inner_curr = 0
        while inner_curr < len(block_data):
            val, n_off, v_type, name = decoder.decode_next_value(block_data, inner_curr)
            if v_type in ["EOF", "NO_HEADER", "DECODE_FAILED"]:
                break
            if name == 'feat_id':
                f_id = val
            elif name == 'body_id':
                b_id = val
            
            if n_off <= inner_curr:
                inner_curr += 1
            else:
                inner_curr = n_off
        
        if f_id is not None or b_id is not None:
            print(f"Block at {off + block_start}: feat_id={f_id}, body_id={b_id}")
            
        curr = block_end

if __name__ == "__main__":
    scan_all_pairs('D:/AI/PROBA/models/00080-03.prt')
