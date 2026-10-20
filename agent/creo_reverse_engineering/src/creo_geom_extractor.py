import re
import os
import sys
import struct

# Добавляем пути для импортов
sys.path.append('D:/AI/tools/agent')
sys.path.append('D:/AI/tools/agent/creo_reverse_engineering/src')

from creo_protocol_decoder import CreoProtocolDecoder
from plm_reader.creo_read import parse_toc, read

def _detect_endianness(data: bytes) -> str:
    """Определяет порядок байтов по заголовку MACH."""
    if b"MACH SUN_SunOS" in data[:1024]:
        return '>'
    return '<'

def scan_all_features(file_path):
    """
    Сканирует AllFeatur, используя feat_id как якорь для разделения записей.
    Это делает парсинг устойчивым к мусору между записями.
    """
    print(f"--- [V3] Record-Centric Scan (AllFeatur): {file_path} ---")
    try:
        data = read(file_path)
        toc = parse_toc(data)
        
        if 'AllFeatur' not in toc:
            print("Error: AllFeatur section not found in TOC.")
            return []
            
        feat_off, feat_len = toc['AllFeatur']
        feat_data = data[feat_off : feat_off + feat_len]
        
        endian = _detect_endianness(data)
        print(f"Detected endianness: {'Big-Endian' if endian == '>' else 'Little-Endian'}")
        decoder = CreoProtocolDecoder(endian=endian)
        
        # 1. Находим позиции всех feat_id
        # Ищем паттерн: [e0] [01] [feat_id] [\0]
        feat_id_pattern = b'\xe0\x01feat_id\x00'
        id_positions = []
        pos = feat_data.find(feat_id_pattern)
        while pos != -1:
            id_positions.append(pos)
            pos = feat_data.find(feat_id_pattern, pos + 1)
            
        print(f"Найдено потенциальных feat_id: {len(id_positions)}")
        
        if not id_positions:
            print("Warning: No feat_id anchors found. The file might be corrupted or use a different format.")
            return []

        results = []
        
        # 2. Разрезаем данные на записи на основе найденных позиций
        for i in range(len(id_positions)):
            start_pos = id_positions[i]
            # Конец записи — это начало следующей позиции или конец данных
            end_pos = id_positions[i+1] if i+1 < len(id_positions) else len(feat_data)
            
            record_data = feat_data[start_pos:end_pos]
            
            # 3. Парсим запись с помощью декодера
            feature = {
                'id': None,
                'body_id': None,
                'params': [],
                'offset': feat_off + start_pos,
                'record': record_data
            }
            
            # Используем локальный декодер для этой записи
            # Чтобы не зависеть от внешнего смещения
            rec_curr = 0
            while rec_curr < len(record_data):
                val, next_off, v_type, name = decoder.decode_next_value(record_data, rec_curr)
                
                if v_type in ["EOF", "NO_HEADER", "DECODE_FAILED"]:
                    break
                
                if name == 'feat_id':
                    feature['id'] = str(val)
                elif name == 'body_id':
                    feature['body_id'] = str(val)
                
                if name:
                    feature['params'].append({'name': name, 'value': val, 'type': v_type})
                
                if next_off <= rec_curr:
                    break
                rec_curr = next_off
                
            if feature['id']:
                results.append(feature)
            else:
                print(f"Warning: Found record at {start_pos} but no feat_id parsed.")

        print(f"Успешно извлечено признаков: {len(results)}")
        return results

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Ошибка при сканировании: {e}")
        return []

if __name__ == "__main__":
    test_file = r"D:\AI\PROBA\models\00080-03.prt"
    if os.path.exists(test_file):
        all_feats = scan_all_features(test_file)
        for feat in all_feats:
            print(f"ID: {feat['id']} | BodyID: {feat['body_id']} | Params: {len(feat['params'])}")
    else:
        print(f"Test file not found: {test_file}")
