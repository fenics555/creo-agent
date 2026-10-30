import sys
sys.path.append('D:/AI/tools/agent/plm_reader')
sys.path.append('D:/AI/tools/agent/creo_reverse_engineering/src')
from creo_read import parse_toc, read
from creo_protocol_decoder import CreoProtocolDecoder

def debug_extractor():
    file_path = r"D:\AI\PROBA\models\00080-03.prt"
    try:
        data = read(file_path)
        toc = parse_toc(data)
        if 'AllFeatur' not in toc:
            print("AllFeatur not in TOC")
            return
            
        feat_off, feat_len = toc['AllFeatur']
        feat_data = data[feat_off : feat_off + feat_len]
        
        endian = '<' # Default
        decoder = CreoProtocolDecoder(endian=endian)
        
        curr = 0
        count = 0
        print(f"Starting debug loop. Data len: {len(feat_data)}")
        while curr < len(feat_data):
            val, next_off, v_type, name = decoder.decode_next_value(feat_data, curr)
            # Use repr() to avoid UnicodeEncodeError
            print(f"Iter {count}: Type={repr(v_type)}, Name={repr(name)}, Val={repr(val)}, Next_off={next_off}, Curr={curr}")
            
            if v_type in ["EOF", "NO_HEADER", "DECODE_FAILED"]:
                print("Stopping: Found terminal type.")
                break
            
            if next_off <= curr:
                print("Stopping: next_off <= curr.")
                break
                
            curr = next_off
            count += 1
            
        print(f"Finished. Total iterations: {count}")
        
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_extractor()

import sys
sys.path.append('D:/AI/tools/agent/plm_reader')
sys.path.append('D:/AI/tools/agent/creo_reverse_engineering/src')
from creo_read import parse_toc, read
from creo_protocol_decoder import CreoProtocolDecoder

def debug_extractor():
    file_path = r"D:\AI\PROBA\models\00080-03.prt"
    try:
        data = read(file_path)
        toc = parse_toc(data)
        if 'AllFeatur' not in toc:
            print("AllFeatur not in TOC")
            return
            
        feat_off, feat_len = toc['AllFeatur']
        feat_data = data[feat_off : feat_off + feat_len]
        
        endian = '<' # Default
        decoder = CreoProtocolDecoder(endian=endian)
        
        curr = 0
        count = 0
        print(f"Starting debug loop. Data len: {len(feat_data)}")
        while curr < len(feat_data):
            val, next_off, v_type, name = decoder.decode_next_value(feat_data, curr)
            print(f"Iter {count}: Type={v_type}, Name={name}, Val={val}, Next_off={next_off}, Curr={curr}")
            
            if v_type in ["EOF", "NO_HEADER", "DECODE_FAILED"]:
                print("Stopping: Found terminal type.")
                break
            
            if next_off <= curr:
                print("Stopping: next_off <= curr.")
                break
                
            curr = next_off
            count += 1
            
        print(f"Finished. Total iterations: {count}")
        
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_extractor()

import sys
sys.path.append('D:/AI/tools/agent/plm_reader')
from creo_read import parse_toc, read
from creo_protocol_decoder import CreoProtocolDecoder

def debug_extractor():
    file_path = r"D:\AI\PROBA\models\00080-03.prt"
    try:
        data = read(file_path)
        toc = parse_toc(data)
        if 'AllFeatur' not in toc:
            print("AllFeatur not in TOC")
            return
            
        feat_off, feat_len = toc['AllFeatur']
        feat_data = data[feat_off : feat_off + feat_len]
        
        endian = '<' # Default
        decoder = CreoProtocolDecoder(endian=endian)
        
        curr = 0
        count = 0
        print(f"Starting debug loop. Data len: {len(feat_data)}")
        while curr < len(feat_data):
            val, next_off, v_type, name = decoder.decode_next_value(feat_data, curr)
            print(f"Iter {count}: Type={v_type}, Name={name}, Val={val}, Next_off={next_off}, Curr={curr}")
            
            if v_type in ["EOF", "NO_HEADER", "DECODE_FAILED"]:
                print("Stopping: Found terminal type.")
                break
            
            if next_off <= curr:
                print("Stopping: next_off <= curr.")
                break
                
            curr = next_off
            count += 1
            
        print(f"Finished. Total iterations: {count}")
        
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_extractor()
