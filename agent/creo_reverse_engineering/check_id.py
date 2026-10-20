import sys
import os

sys.path.insert(0, 'D:/AI/tools/agent')
sys.path.insert(0, 'D:/AI/tools/agent/creo_reverse_engineering/src')

from plm_reader.creo_read import read
from creo_protocol_decoder import CreoProtocolDecoder

def check_id(file_path, target_id):
    data = read(file_path)
    decoder = CreoProtocolDecoder()
    
    # GeomDepen: (15527, 422)
    d_off, d_len = 15527, 422
    depen_data = data[d_off:d_off+d_len]
    
    print(f"Searching for body_id {target_id} in GeomDepen...")
    curr = 0
    found = False
    while curr < len(depen_data):
        val, n_off, v_type, name = decoder.decode_next_value(depen_data, curr)
        if v_type in ["EOF", "NO_HEADER", "DECODE_FAILED"]:
            break
        if v_type == 'INT' and name == 'body_id' and val == target_id:
            print(f"  SUCCESS: Found body_id {val}!")
            found = True
            break
        curr = n_off if n_off > curr else curr + 1
    
    if not found:
        print(f"  FAILED: body_id {target_id} not found.")

if __name__ == "__main__":
    # Test for 9611509
    check_id('D:/AI/PROBA/models/00080-03.prt', 9611509)
    # Test for 1
    check_id('D:/AI/PROBA/models/00080-03.prt', 1)
