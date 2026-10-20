import struct

class CreoProtocolDecoder:
    """
    'РњРѕР·Рі' РїР°СЂСЃРµСЂР°. 
    Р”РµРєРѕРґРёСЂСѓРµС‚ РїСЂРѕРїСЂРёРµС‚Р°СЂРЅС‹Р№ Р±РёРЅР°СЂРЅС‹Р№ РїСЂРѕС‚РѕРєРѕР» Creo, РѕР±СЂР°Р±Р°С‚С‹РІР°СЏ both:
    1. [e0] [type_byte] [name]\\0 [value] -> Strict Length Parsing (РЅР°РґРµР¶РЅРѕ)
    2. [name]\\0 [value] (Inferred type)
    """

    # РљРѕРЅС„РёРіСѓСЂР°С†РёСЏ С‚РёРїРѕРІ РґР»СЏ СЂРµР¶РёРјР° [e0]: type_byte -> (length, struct_format)
    TYPE_CONFIG = {
        0x00: (0, 'h'),   # HEADER
        0x01: (4, 'I'),   # INT
        0x02: (0, 's'),   # STRING
        0x03: (8, 'd'),   # DOUBLE
    }
    def __init__(self, endian='<'):
        self.endian = endian



    def _clean_name(self, name: str) -> str:
        """Очищает имя от управляющих символов и лишних пробелов."""
        # 1. Удаляем непечатные символы
        cleaned = "".join(c for c in name if 32 <= ord(c) <= 126)
        # 2. Удаляем мусорные знаки препинания по краям
        return cleaned.strip("()[]{}!@#$%^&*+=- ")

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
                name = self._clean_name(data[name_start:name_end].decode('utf-8', errors='ignore'))
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
                name_end = data.find(b'\x00', curr)
                if name_end == -1:
                    return None, data_len, "EOF", ""

                name = self._clean_name(data[curr:name_end].decode('utf-8', errors='ignore'))
                if not name or len(name) < 2:
                    curr = name_end + 1
                    continue

                val_start = name_end + 1
                # Р’ fallback-СЂРµР¶РёРјРµ РёСЃРїРѕР»СЊР·СѓРµРј СЌРІСЂРёСЃС‚РёРєСѓ РїРѕРёСЃРєР° РіСЂР°РЅРёС†
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

                # Р­РІСЂРёСЃС‚РёРєР° С‚РёРїРѕРІ РґР»СЏ fallback-СЂРµР¶РёРјР°
                # РџС‹С‚Р°РµРјСЃСЏ INT (4 Р±Р°Р№С‚Р°)
                if len(val_raw) >= 4:
                    for fmt in ['<I', '>I']:
                        try:
                            val = struct.unpack(fmt, val_raw[:4])[0]
                            if 0 < val < 100000000:
                                return val, val_end, "INT", name
                        except: continue

                # РџС‹С‚Р°РµРјСЃСЏ DOUBLE (8 Р±Р°Р№С‚)
                if len(val_raw) >= 8:
                    try:
                        val = struct.unpack('>d', val_raw[:8])[0]
                        if abs(val) < 1e15 and abs(val) > 1e-18:
                            return val, val_end, "DOUBLE", name
                    except: pass

                # РџРѕ СѓРјРѕР»С‡Р°РЅРёСЋ STRING
                try:
                    s_val = val_raw.decode('utf-8', errors='ignore').strip()
                    return s_val if s_val else name, val_end, "STRING", name
                except:
                    return val_raw.hex(), val_end, "HEX_FALLBACK", name

        return None, curr, "EOF", ""


if __name__ == "__main__":
    print("--- TEST 1: Strict INT (Little Endian) ---")
    decoder = CreoProtocolDecoder(endian='<')
    # [e0] [01] [body_id] [\x00] [val=12345 in 4 bytes LE]
    test_data = b'\xe0\x01body_id\x00\x39\x30\x00\x00'
    print(decoder.decode_next_value(test_data, 0))

    print("\n--- TEST 2: Strict DOUBLE with 0xe0 inside (Big Endian) ---")
    decoder = CreoProtocolDecoder(endian='>')
    # РЎРѕР·РґР°РµРј double, РєРѕС‚РѕСЂС‹Р№ СЃРѕРґРµСЂР¶РёС‚ Р±Р°Р№С‚ 0xe0 РІ СЃРІРѕРµРј РїСЂРµРґСЃС‚Р°РІР»РµРЅРёРё
    # 1.0 РІ BE: 3ff0000000000000. 
    # Р’РѕР·СЊРјРµРј РґСЂСѓРіРѕРµ Р·РЅР°С‡РµРЅРёРµ. РќР°РїСЂРёРјРµСЂ, Р±Р°Р№С‚С‹: \xe0\x00\x00\x00\x00\x00\x00\x00
    double_with_e0 = b'\xe0\x00\x00\x00\x00\x00\x00\x00\xe0'
    test_data = b'\xe0\x03val_with_e0\x00' + double_with_e0
    print(decoder.decode_next_value(test_data, 0))

    print("\n--- TEST 3: String (non-e0) ---")
    decoder = CreoProtocolDecoder()
    test_data = b'my_name\x00hello\x00'
    print(decoder.decode_next_value(test_data, 0))
