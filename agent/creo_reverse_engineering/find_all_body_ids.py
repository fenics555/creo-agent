import sys
import os

sys.path.insert(0, 'D:/AI/tools/agent')
sys.path.insert(0, 'D:/AI/tools/agent/creo_reverse_engineering/src')

from plm_reader.creo_read import read
from creo_protocol_decoder import CreoProtocolDecoder

def find_all_body_ids(file_path):
    data = read(file_path)
    decoder = CreoProtocolDecoder()
    
    print(f"--- Scanning {file_path} for all body_id fields ---")
    
    curr = 0
    count = 0
    while curr < len(data):
        val, n_off, v_type, name = decoder.decode_next_value(data, curr)
        
        if v_type in ["EOF", "NO_HEADER", "DECODE_FAILED"]:
            break
            
        if v_type == 'INT' and name == 'body_id':
            print(f"  [FOUND] body_id: {val} at offset {curr}")
            count += 1
            
        if n_off <= curr:
            curr += 1
        else:
            curr = n_off
            
    print(f"\nScan finished. Found {count} body_id fields.")

if __name__ == "__main__":
    find_all_body_ids('D:/AI/PROBA/models/00080-03.prt')
