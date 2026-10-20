import re
import os
import sys
sys.path.append('D:/AI/tools/agent')
from creo_protocol_decoder import CreoProtocolDecoder
from plm_reader.creo_read import parse_toc

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
        from plm_reader.creo_read import read
        data = read(file_path)
        toc = parse_toc(data)
        
        if 'AllFeatur' not in toc:
            print("Error: AllFeatur section not found in TOC.")
            return []
            
        feat_off, feat_len = toc['AllFeatur']
        feat_data = data[feat_off : feat_off + feat_len]
        
        decoder = CreoProtocolDecoder()
        results = []
        
        current_feature = None
        
        # Сканируем все e0 блоки в AllFeatur
        curr = 0
        while curr < len(feat_data):
            val, next_off, v_type, name = decoder.decode_next_value(feat_data, curr)
            
            if v_type in ["EOF", "NO_HEADER", "DECODE_FAILED"]:
                break
            
            # Если мы нашли field, который является идентификатором, начинаем новый признак
            if name in ['feat_id', 'body_id']:
                if current_feature:
                    results.append(current_feature)
                
                current_feature = {
                    'id': str(val) if name == 'feat_id' else None,
                    'body_id': str(val) if name == 'body_id' else None,
                    'params': [],
                    'offset': feat_off + curr
                }
                # Если это был body_id, мы всё равно должны добавить его в params для полноты
                current_feature['params'].append({'name': name, 'value': val, 'type': v_type})
            else:
                if current_feature:
                    current_feature['params'].append({'name': name, 'value': val, 'type': v_type})
                else:
                    # Если нашли поле до первого ID - это какой-то системный блок или мусор
                    pass

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
    test_file = r"D:\AI\PROBA\models\00080-03.prt"
    all_feats = scan_all_features(test_file)
    for feat in all_feats:
        print(f"ID: {feat['id']} | BodyID: {feat['body_id']} | Params: {len(feat['params'])}")
