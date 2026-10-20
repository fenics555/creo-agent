import sys
import os

sys.path.insert(0, 'D:/AI/tools/agent')
sys.path.insert(0, 'D:/AI/tools/agent/creo_reverse_engineering/src')

from plm_reader.creo_read import read
from creo_protocol_decoder import CreoProtocolDecoder

def scan_depen_for_all_ids(file_path):
    data = read(file_path)
    decoder = CreoProtocolDecoder()
    
    # GeomDepen: (15527, 422)
    d_off, d_len = 15527, 422
    depen_data = data[d_off:d_off+d_len]
    
    print(f"--- Scanning GeomDepen at {d_off} ---")
    
    curr = 0
    while curr < len(depen_data):
        val, n_off, v_type, name = decoder.decode_next_value(depen_data, curr)
        if v_type in ["EOF", "NO_HEADER", "DECODE_FAILED"]:
            break
        
        if v_type == 'INT':
            print(f"  [INT] {name}: {val}")
        elif v_type == 'STRING':
            print(f"  [STR] {name}: {val}")
        else:
            print(f"  [{v_type}] {name}: {val}")
            
        curr = n_off if n_off > curr else curr + 1

if __name__ == "__main__":
    scan_depen_for_all_ids('D:/AI/PROBA/models/00080-03.prt')
