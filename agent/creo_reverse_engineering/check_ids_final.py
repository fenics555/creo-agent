import sys
import os
sys.path.append('D:/AI/tools/agent')
from plm_reader.creo_read import read
from creo_protocol_decoder import CreoProtocolDecoder

def check_body_ids(file_path):
    data = read(file_path)
    decoder = CreoProtocolDecoder()
    
    # GeomDepen
    d_off, d_len = 15527, 422
    depen_data = data[d_off:d_off+d_len]
    print("--- GeomDepen ---")
    curr = 0
    while curr < len(depen_data):
        val, n_off, v_type, name = decoder.decode_next_value(depen_data, curr)
        if v_type == 'INT' and name == 'body_id':
            print(f"  Found body_id: {val}")
        if n_off <= curr: break
        curr = n_off

    # AllFeatur
    f_off, f_len = 27069, 3789
    feat_data = data[f_off:f_off+f_len]
    print("\n--- AllFeatur ---")
    curr = 0
    while curr < len(feat_data):
        val, n_off, v_type, name = decoder.decode_next_value(feat_data, curr)
        if v_type == 'INT' and name == 'body_id':
            print(f"  Found body_id: {val}")
        if n_off <= curr: break
        curr = n_off

if __name__ == "__main__":
    check_body_ids('D:/AI/PROBA/models/00080-03.prt')
