import sys
import os
sys.path.insert(0, 'D:/AI/tools/agent')
sys.path.insert(0, os.path.join('D:/AI/tools/agent', 'creo_reverse_engineering', 'src'))
from plm_reader.creo_read import read
from creo_protocol_decoder import CreoProtocolDecoder

def analyze_geom_depen(file_path, offset, length):
    data = read(file_path)
    depen_data = data[offset : offset + length]
    decoder = CreoProtocolDecoder()
    
    print(f"Analyzing GeomDepen at {offset} (len {length})...\n")
    
    curr = 0
    while curr < len(depen_data):
        val, n_off, v_type, name = decoder.decode_next_value(depen_data, curr)
        
        if v_type in ["EOF", "NO_HEADER", "DECODE_FAILED"]:
            break
            
        print(f"Type: {v_type:15} | Name: {name:20} | Val: {val}")
        
        if n_off <= curr:
            curr += 1
        else:
            curr = n_off

if __name__ == "__main__":
    analyze_geom_depen('D:/AI/PROBA/models/00080-03.prt', 15527, 422)
