import re
from creo_protocol_decoder import CreoProtocolDecoder

def extract_params_via_protocol(record_data):
    """
    Использует протокол для последовательного разбора параметров внутри записи.
    Возвращает список найденных значений (тип, значение).
    """
    decoder = CreoProtocolDecoder()
    params = []
    offset = 0
    
    while offset < len(record_data):
        val, next_off, v_type = decoder.decode_next_value(record_data, offset)
        
        if v_type in ["EOF", "NO_HEADER", "DECODE_FAILED"]:
            break
        
        if v_type == "DOUBLE":
            params.append(("DOUBLE", val))
        elif v_type == "INT":
            params.append(("INT", val))
        elif v_type == "STRING":
            params.append(("STRING", val))
            
        if next_off <= offset:
            break
        offset = next_off
        
    return params

def scan_all_features(file_path):
    """Сканирует файл, используя протокол для извлечения параметров каждого признака."""
    print(f"--- Protocol-Aware Scan: {file_path} ---")
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
            
            pattern = re.compile(b'feat_defs_')
            matches = list(pattern.finditer(data))
            
            print(f"Найдено признаков: {len(matches)}")
            
            results = []
            for i, m in enumerate(matches):
                feat_start = m.start()
                
                if i + 1 < len(matches):
                    feat_end = matches[i+1].start()
                else:
                    feat_end = len(data)
                
                record_data = data[feat_start:feat_end]
                
                id_match = re.search(b'feat_defs_([a-zA-Z0-9_]+)', record_data)
                if id_match:
                    raw_feat_id = id_match.group(1).decode('utf-8', errors='ignore')
                    id_digits = re.search(r'\d+', raw_feat_id)
                    feat_id = id_digits.group() if id_digits else raw_feat_id
                else:
                    feat_id = f"unknown_{feat_start}"

                params = extract_params_via_protocol(record_data)
                
                results.append({
                    'id': feat_id,
                    'offset': feat_start,
                    'record': record_data, # Added for classification
                    'params': params
                })
            
            return results
    except Exception as e:
        print(f"Ошибка при сканировании: {e}")
        return []

if __name__ == "__main__":
    test_file = r"D:\AI\PROBA\models\23-1017GRI 2кап чистовой BDF 5 1_2''\23-1017gri-02.prt.1"
    all_feats = scan_all_features(test_file)
    for feat in all_feats:
        # Safe print for Windows terminal
        out = f"ID: {feat['id']} | Params: {feat['params']}"
        print(out.encode('cp1251', errors='replace').decode('cp1251'))
