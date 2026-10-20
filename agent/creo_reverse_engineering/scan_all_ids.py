import sys
import os

sys.path.insert(0, 'D:/AI/tools/agent')
sys.path.insert(0, 'D:/AI/tools/agent/creo_reverse_engineering/src')

from plm_reader.creo_read import read
from creo_protocol_decoder import CreoProtocolDecoder

def scan_all_ids_in_all_featur(file_path):
    data = read(file_path)
    decoder = CreoProtocolDecoder()
    
    # AllFeatur: (27069, 3789)
    off, length = 27069, 3789
    feat_data = data[off:off+length]
    
    print(f"--- Scanning AllFeatur ({off}:{off+length}) for IDs ---")
    
    curr = 0
    while curr < len(feat_data):
        val, n_off, v_type, name = decoder.decode_next_value(feat_data, curr)
        
        if v_type in ["EOF", "NO_HEADER", "DECODE_FAILED"]:
            break
            
        if name in ['feat_id', 'body_id']:
            print(f"  [{name}] {val} (Type: {v_type}) at offset {off + curr}")
        
        if n_off <= curr:
            curr += 1
        else:
            curr = n_off
            
    print("\nScan finished.")

if __name__ == "__main__":
    scan_all_ids_in_all_featur('D:/AI/PROBA/models/00080-03.prt')
