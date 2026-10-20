import sys
import os
import json

# Настройка путей
sys.path.insert(0, 'D:/AI/tools/agent')
sys.path.insert(0, os.path.join('D:/AI/tools/agent', 'creo_reverse_engineering', 'src'))

from plm_reader.creo_read import read
from creo_protocol_decoder import CreoProtocolDecoder

def analyze_features_deep(file_path):
    data = read(file_path)
    decoder = CreoProtocolDecoder()
    
    # Нам нужно найти смещение FeatDefs. Для теста возьмем из примера или найдем через TOC.
    # Но так как мы в режиме исследования, лучше сначала распарсить TOC.
    from creo_read import parse_toc
    toc = parse_toc(data)
    if not toc or 'FeatDefs' not in toc:
        print("Error: FeatDefs not found in TOC")
        return

    feat_off, feat_len = toc['FeatDefs']
    feat_data = data[feat_off : feat_off + feat_len]
    
    print(f"--- Deep Scan: FeatDefs at {feat_off} (len {feat_len}) ---\n")
    
    # Ищем маркеры feat_defs_
    import re
    pattern = re.compile(b'feat_defs_')
    matches = list(pattern.finditer(feat_data))
    
    print(f"Found {len(matches)} feature markers.\n")
    
    for i, m in enumerate(matches):
        start = m.start()
        # Определяем конец записи (до следующего маркера или конец блока)
        end = matches[i+1].start() if i+1 < len(matches) else len(feat_data)
        record = feat_data[start:end]
        
        # Извлекаем ID
        id_match = re.search(b'feat_defs_([a-zA-Z0-9_]+)', record)
        feat_id = id_match.group(1).decode('utf-8') if id_match else f"unknown_{start}"
        
        print(f"--- Feature ID: {feat_id} (Offset: {feat_off + start}) ---")
        
        # Декодируем содержимое записи
        curr = 0
        while curr < len(record):
            val, n_off, v_type, name = decoder.decode_next_value(record, curr)
            if v_type in ["EOF", "NO_HEADER", "DECODE_FAILED"]:
                break
            
            print(f"  [{v_type:10}] {name:25} : {val}")
            
            if n_off <= curr:
                curr += 1
            else:
                curr = n_off
        print("-" * 50)

if __name__ == "__main__":
    analyze_features_deep('D:/AI/PROBA/models/00080-03.prt')
