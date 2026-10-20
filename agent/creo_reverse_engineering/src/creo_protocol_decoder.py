import struct

class CreoProtocolDecoder:
    """
    The 'Brain' of the parser. 
    Decodes the proprietary Creo binary protocol, handling both:
    1. [e0] [type_byte] [name]\0 [value]
    2. [name]\0 [value] (Inferred type)
    """
    
    def __init__(self):
        pass

    def decode_next_value(self, data: bytes, offset: int):
        """
        Searches for the next field and decodes it.
        Returns: (decoded_value, next_offset, value_type, name)
        """
        curr = offset
        
        while curr < len(data):
            # 1. Check if current position is an 'e0' header
            if data[curr:curr+1] == b'\xe0':
                # Protocol mode: [e0] [type_byte] [name]\0 [value]
                if curr + 2 >= len(data):
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
                
                # Find the end of the value: next 'e0' or EOF
                next_e0 = data.find(b'\xe0', val_start)
                if next_e0 == -1:
                    val_end = len(data)
                else:
                    val_end = next_e0
                
                val_raw = data[val_start:val_end]
                
                if type_byte == 0x00: # HEADER / NAME ONLY
                    return None, val_end, "HEADER", name

                # Parse val_raw based on type_byte
                try:
                    if type_byte == 0x01: # INT
                        # Try different lengths (1 to 4 bytes)
                        for length in [4, 3, 2, 1]:
                            if len(val_raw) >= length:
                                if length == 4:
                                    try:
                                        val = struct.unpack('<I', val_raw[:4])[0]
                                        if 0 < val < 100000000: return val, val_end, "INT", name
                                    except: pass
                                    try:
                                        val = struct.unpack('>I', val_raw[:4])[0]
                                        if 0 < val < 100000000: return val, val_end, "INT", name
                                    except: pass
                                elif length == 3:
                                    val = int.from_bytes(val_raw[:3], 'little')
                                    if 0 < val < 100000000: return val, val_end, "INT", name
                                elif length == 2:
                                    try:
                                        val = struct.unpack('<H', val_raw[:2])[0]
                                        if 0 < val < 100000000: return val, val_end, "INT", name
                                    except: pass
                                    try:
                                        val = struct.unpack('>H', val_raw[:2])[0]
                                        if 0 < val < 100000000: return val, val_end, "INT", name
                                    except: pass
                                elif length == 1:
                                    val = val_raw[0]
                                    if 0 < val < 100000000: return val, val_end, "INT", name
                                break
                        # If no length worked, fallback
                        return val_raw.hex(), val_end, "HEX_FALLBACK", name
                        
                    elif type_byte == 0x02: # STRING
                        if not val_raw:
                            return name, val_end, "STRING", name
                        s_val = val_raw.decode('utf-8', errors='ignore').strip()
                        return s_val if s_val else name, val_end, "STRING", name
                        
                    elif type_byte == 0x03: # DOUBLE
                        if len(val_raw) >= 8:
                            val = struct.unpack('>d', val_raw[:8])[0]
                            if abs(val) < 1e15 and abs(val) > 1e-18:
                                return val, val_end, "DOUBLE", name
                    else:
                        return None, val_end, f"UNKNOWN_{type_byte:02X}", name
                except Exception as e:
                    print(f"DEBUG: Error decoding {name}: {e}")
                    return val_raw.hex(), val_end, "HEX_FALLBACK", name
                
                curr = val_end
                continue

            # 2. Non-e0 mode: [name]\0 [value]
            name_end = data.find(b'\x00', curr)
            if name_end == -1:
                return None, len(data), "EOF", ""
            
            name = data[curr:name_end].decode('utf-8', errors='ignore').strip()
            if not name or len(name) < 2:
                curr = name_end + 1
                continue

            val_start = name_end + 1
            next_null = data.find(b'\x00', val_start)
            next_e0 = data.find(b'\xe0', val_start)
            
            if next_null == -1 and next_e0 == -1:
                val_end = len(data)
            elif next_null == -1:
                val_end = next_e0
            elif next_e0 == -1:
                val_end = next_null
            else:
                val_end = min(next_null, next_e0)
            
            val_raw = data[val_start:val_end]

            # Try to infer type
            if len(val_raw) >= 4:
                for fmt in ['<I', '>I']:
                    try:
                        val = struct.unpack(fmt, val_raw[:4])[0]
                        if 0 < val < 100000000:
                            return val, val_end, "INT", name
                    except:
                        continue
            
            if len(val_raw) >= 8:
                try:
                    val = struct.unpack('>d', val_raw[:8])[0]
                    if abs(val) < 1e15 and abs(val) > 1e-18:
                        return val, val_end, "DOUBLE", name
                except:
                    pass
            
            try:
                s_val = val_raw.decode('utf-8', errors='ignore').strip()
                return s_val if s_val else name, val_end, "STRING", name
            except:
                return val_raw.hex(), val_end, "HEX_FALLBACK", name

        return None, curr, "EOF", ""

if __name__ == "__main__":
    decoder = CreoProtocolDecoder()
    print("--- TEST 1: 3-byte INT ---")
    test_data = b'\xe0\x01body_id\x00\xf5\x96\x92'
    print(decoder.decode_next_value(test_data, 0))

    print("\n--- TEST 2: String (non-e0) ---")
    test_data = b'my_name\x00hello\x00'
    print(decoder.decode_next_value(test_data, 0))
