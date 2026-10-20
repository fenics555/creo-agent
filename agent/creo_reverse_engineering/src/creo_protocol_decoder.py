import struct

class CreoProtocolDecoder:
    TYPE_CONFIG = {0x00: (0, 'h'), 0x01: (4, 'I'), 0x02: (0, 's'), 0x03: (8, 'd')}
    def __init__(self, endian='<'):
        self.endian = endian


    def decode_next_value(self, data: bytes, offset: int):
        """
        Ищет следующее поле и декодирует его.
        Возвращает: (decoded_value, next_offset, value_type, name)
        """
        curr = offset



if __name__ == "__main__":
    print("--- TEST 1: Strict INT (Little Endian) ---")
    decoder = CreoProtocolDecoder(endian='<')
    # [e0] [01] [body_id] [\x00] [val=12345 in 4 bytes LE]
    test_data = b'\xe0\x01body_id\x00\x39\x30\x00\x00'
    print(decoder.decode_next_value(test_data, 0))

    print("\n--- TEST 2: Strict DOUBLE with 0xe0 inside (Big Endian) ---")
    decoder = CreoProtocolDecoder(endian='>')
    # Создаем double, который содержит байт 0xe0 в своем представлении
    # 1.0 в BE: 3ff0000000000000. 
    # Возьмем другое значение. Например, байты: \xe0\x00\x00\x00\x00\x00\x00\x00
    double_with_e0 = b'\xe0\x00\x00\x00\x00\x00\x00\x00\xe0'
    test_data = b'\xe0\x03val_with_e0\x00' + double_with_e0
    print(decoder.decode_next_value(test_data, 0))

    print("\n--- TEST 3: String (non-e0) ---")
    decoder = CreoProtocolDecoder()
    test_data = b'my_name\x00hello\x00'
    print(decoder.decode_next_value(test_data, 0))

                name_end = data.find(b'\x00', curr)
                if name_end == -1:
                    return None, data_len, "EOF", ""

                name = data[curr:name_end].decode('utf-8', errors='ignore').strip()
                if not name or len(name) < 2:
                    curr = name_end + 1
                    continue

                val_start = name_end + 1
                # В fallback-режиме используем эвристику поиска границ
                next_null = data.find(b'\x00', val_start)
                next_e0 = data.find(b'\xe0', val_start)

                if next_null == -1 and next_e0 == -1:
                    val_end = data_len
                elif next_null == -1:
                    val_end = next_e0
                elif next_e0 == -1:
                    val_end = next_null
                else:
                    val_end = min(next_null, next_e0)

                val_raw = data[val_start:val_end]
                if not val_raw:
                    curr = val_end
                    return "", curr, "STRING", name

                # Эвристика типов для fallback-режима
                # Пытаемся INT (4 байта)
                if len(val_raw) >= 4:
                    for fmt in ['<I', '>I']:
                        try:
                            val = struct.unpack(fmt, val_raw[:4])[0]
                            if 0 < val < 100000000:
                                return val, val_end, "INT", name
                        except: continue

                # Пытаемся DOUBLE (8 байт)
                if len(val_raw) >= 8:
                    try:
                        val = struct.unpack('>d', val_raw[:8])[0]
                        if abs(val) < 1e15 and abs(val) > 1e-18:
                            return val, val_end, "DOUBLE", name
                    except: pass

                # По умолчанию STRING
                try:
                    s_val = val_raw.decode('utf-8', errors='ignore').strip()
                    return s_val if s_val else name, val_end, "STRING", name
                except:
                    return val_raw.hex(), val_end, "HEX_FALLBACK", name

        return None, curr, "EOF", ""

        data_len = len(data)

        while curr < data_len:
            # --- РЕЖИМ 1: [e0] [type_byte] [name]\\0 [value] ---
            if data[curr:curr+1] == b'\xe0':
                if curr + 2 >= data_len:
                    curr += 1
                    continue

                type_byte = data[curr + 1]
                name_start = curr + 2
                
                # Ищем конец имени (нулевой байт)
                name_end = data.find(b'\x00', name_start)
                if name_end == -1:
                    curr += 1
                    continue

                name = data[name_start:name_end].decode('utf-8', errors='ignore').strip()
                val_start = name_end + 1

                # Если тип 0x00 — это просто заголовок/имя
                if type_byte == 0x00:
                    curr = val_start
                    return None, curr, "HEADER", name

                config = self.TYPE_CONFIG.get(type_byte)
                if not config:
                    # Неизвестный тип: ищем следующий e0, чтобы не потерять синхронизацию
                    next_e0 = data.find(b'\xe0', val_start)
                    val_end = next_e0 if next_e0 != -1 else data_len
                    curr = val_end
                    return None, curr, f"UNKNOWN_{type_byte:02X}", name

                length, fmt_char = config

                # --- Strict Length Parsing ---
                if length == 0: # Переменная длина (STRING или HEADER)
                    next_null = data.find(b'\x00', val_start)
                    next_e0 = data.find(b'\xe0', val_start)
                    
                    if next_null == -1 and next_e0 == -1:
                        val_end = data_len
                    elif next_null == -1:
                        val_end = next_e0
                    elif next_e0 == -1:
                        val_end = next_null
                    else:
                        val_end = min(next_null, next_e0)
                    
                    val_raw = data[val_start:val_end]
                    try:
                        val = val_raw.decode('utf-8', errors='ignore').strip()
                    except:
                        val = val_raw.hex()
                    
                    curr = val_end
                    return val, curr, "STRING", name

                else: # Фиксированная длина (INT, DOUBLE)
                    if val_start + length > data_len:
                        curr = data_len
                        return None, curr, "EOF", name
                    
                    val_raw = data[val_start:val_start + length]
                    try:
                        fmt = f"{self.endian}{fmt_char}"
                        val = struct.unpack(fmt, val_raw)[0]
                    except Exception as e:
                        curr = val_start + length
                        return val_raw.hex(), curr, "DECODE_ERROR", name
                    
                    curr = val_start + length
                    v_type = "INT" if type_byte == 0x01 else "DOUBLE"
                    return val, curr, v_type, name

            # --- РЕЖИМ 2: [name]\\0 [value] (Fallback / Inferred) ---
            else:

