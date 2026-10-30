import os

content = r"""import re
import os
import sys
sys.path.append('D:/AI/tools/agent')
sys.path.append('D:/AI/tools/agent/creo_reverse_engineering/src')
from creo_protocol_decoder import CreoProtocolDecoder
from plm_reader.creo_read import parse_toc, read

def _detect_endianness(data: bytes) -> str:
    """Detect endianness from MACH header."""
    if b"MACH SUN_SunOS" in data[:1024]:
        return '>'
    return '<'

def extract_params_via_protocol(decoder, record_data):
    """
    Использует протокол для последовательного разбора параметров внутри записи.
    Возвращает список найденных значений (тип, значение, имя).
    """
    params = []
    offset = 0
    
    while offset < len(record_data):
        val, next_off, v_type, name = decoder.decode_next_value(record_data, offset)
        
        if v_type in ["EOF", "NO_HEADER", "DECODE_FAILED"]:
            break
        
        if name:
            params.append({
                "name": name,
                "value": val,
                "type": v_type
            })
            
        if next_off <= offset:
            break
        offset = next_off
        
    return params

def scan_all_features(file_path):
    """Сканирует AllFeatur для извлечения параметров каждого признака."""
    print(f"--- Protocol-Aware Scan (AllFeatur): {file_path} ---")
    try:
        data = read(file_path)
        toc = parse_toc(data)
        
        if 'AllFeatur' not in toc:
            print("Error: AllFeatur section not found in TOC.")
            return []
            
        feat_off, feat_len = toc['AllFeatur']
        feat_data = data[feat_off : feat_off + feat_len]
        
        # --- NEW: Endianness Detection ---
        endian = _detect_endianness(data)
        print(f"Detected endianness: {'Big-Endian' if endian == '>' else 'Little-Endian'}")
        decoder = CreoProtocolDecoder(endian=endian)
        
        results = []
        current_feature = None
        current_feat_id = None
        
        # Сканируем все e0 блоки в AllFeatur
        curr = 0
        while curr < len(feat_data):
            val, next_off, v_type, name = decoder.decode_next_value(feat_data, curr)
            
            if v_type in ["EOF", "NO_HEADER", "DECODE_FAILED"]:
                break
            
            # Если встретили feat_id — это новый признак или обновление текущего
            if name == 'feat_id':
                if current_feature:
                    results.append(current_feature)
                
                current_feat_id = str(val)
                current_feature = {
                    'id': current_feat_id,
                    'body_id': None,
                    'params': [],
                    'offset': feat_off + curr,
                    'record': feat_data[curr:next_off]
                }
                current_feature['params'].append({'name': name, 'value': val, 'type': v_type})
            
            # Если встретили body_id — привязываем к текущему признаку
            elif name == 'body_id':
                if current_feature:
                    current_feature['body_id'] = str(val)
                else:
                    # Если body_id пришел без feat_id (аномалия), создаем \"безымянный\" признак
                    current_feat_id = None
                    current_feature = {
                        'id': None,
                        'body_id': str(val),
                        'params': [],
                        'offset': feat_off + curr,
                        'record': feat_data[curr:next_off]
                    }
                current_feature['params'].append({'name': name, 'value': val, 'type': v_type})
            
            else:
                # Обычное поле
                if current_feature:
                    current_feature['params'].append({'name': name, 'value': val, 'type': v_type})
                else:
                    # Если нашли поле до первого ID, создаем заглушку
                    current_feat_id = None
                    current_feature = {
                        'id': None,
                        'body_id': None,
                        'params': [],
                        'offset': feat_off + curr,
                        'record': feat_data[curr:next_off]
                    }
                    current_feature['params'].append({'name': name, 'value': val, 'type': v_type})

            if next_off <= curr:
                break
            curr = next_off

        if current_feature:
            results.append(current_feature)
            
        print(f"Найдено признаков: {len(results)}")
        return results

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Ошибка при сканировании: {e}")
        return []

if __name__ == "__main__":
    import sys
    import os
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    sys.path.insert(0, BASE_DIR)
    sys.path.insert(0, os.path.join(BASE_DIR, 'plm_reader'))
    test_file = r"D:\\AI\\PROBA\\models\\00080-03.prt"
    all_feats = scan_all_features(test_file)
    for feat in all_feats:
        print(f"ID: {feat['id']} | BodyID: {feat['body_id']} | Params: {len(feat['params'])}")
"""

target = r"D:\AI\tools\agent\creo_reverse_engineering\src\creo_geom_extractor.py"
with open(target, 'w', encoding='utf-8') as f:
    f.write(content)
print("SUCCESS")
"""
