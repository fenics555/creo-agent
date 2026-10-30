import struct

class CreoProtocolDecoder:
    """
    'Мозг' парсера. 
    Декодирует проприетарный бинарный протокол Creo, обрабатывая both:
    1. [e0] [type_byte] [name]\\0 [value] -> Strict Length Parsing (надежно)
    2. [name]\\0 [value] (Inferred type)
    """

    # Конфигурация типов для режима [e0]: type_byte -> (length, struct_format)
    TYPE_CONFIG = {
        0x00: (0, 'h'),   # HEADER
        0x01: (4, 'I'),   # INT
        0x02: (0, 's'),   # STRING
        0x03: (8, 'd'),   # DOUBLE
    }

    def __init__(self, endian='<'):
        self.endian = endian

    def decode_next_value(self, data: bytes, offset: int):
        curr = offset
        data_len = len(data)
        while curr < data_len:
            if data[curr:curr+1] == b'\xe0':
                if curr + 2 >= data_len:
                    curr += 1
                    continue
                type_byte = data[curr + 1]
                name_start = curr + 2
                name_end = data.find(b'\x00', name_start)
                if name_end == -1:
                    curr += 1
                    continue
                name = data[name_start:name_end].decode('utf-8', errors='ignore').strip()
                val_start = name_end + 1
                if type_byte == 0x00:
                    curr = val_start
                    return None, curr, "HEADER", name
                config = self.TYPE_CONFIG.get(type_byte)
                if not config:
                    next_e0 = data.find(b'\xe0', val_start)
                    val_end = next_e0 if next_e0 != -1 else data_len
                    curr = val_end
                    return None, curr, f"UNKNOWN_{type_byte:02X}", name
                length, fmt_char = config
                if length == 0:
                    next_null = data.find(b'\x00', val_start)
                    next_e0 = data.find(b'\xe0', val_start)
                    if next_null == -1 and next_e0 == -1: val_end = data_len
                    elif next_null == -1: val_end = next_e0
                    elif next_e0 == -1: val_end = next_null
                    else: val_end = min(next_null, next_e0)
                    val_raw = data[val_start:val_end]
                    try: val = val_raw.decode('utf-8', errors='ignore').strip()
                    except: val = val_raw.hex()
                    curr = val_end
                    return val, curr, "STRING", name
                else:
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
            else:
