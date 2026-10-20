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
                
                if type_byte == 0x00: # HEADER / NAME ONLY
                    return None, val_start, "HEADER", name

                if type_byte == 0x01: # INT
                    if val_start + 4 <= len(data):
                        for fmt in ['<I', '>I']:
                            try:
                                val = struct.unpack(fmt, data[val_start:val_start+4])[0]
                                if 0 < val < 100000000:
                                    return val, val_start + 4, "INT", name
                            except:
                                continue
                elif type_byte == 0x02: # STRING
                    if val_start >= len(data):
                        return name, val_start, "STRING", name
                    end_idx = data.find(b'\x00', val_start)
                    if end_idx == -1: end_idx = len(data)
                    try:
                        s_val = data[val_start:end_idx].decode('utf-8', errors='ignore').strip()
                        return s_val if s_val else name, end_idx + 1, "STRING", name
                    except:
                        return name, val_start, "STRING", name
                elif type_byte == 0x03: # DOUBLE
                    if val_start + 8 <= len(data):
                        try:
                            val = struct.unpack('>d', data[val_start:val_start+8])[0]
                            if abs(val) < 1e15 and abs(val) > 1e-18:
                                return val, val_start + 8, "DOUBLE", name
                        except:
                            pass
                else:
                    return None, val_start, f"UNKNOWN_{type_byte:02X}", name
                
                curr += 1
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
            if val_start >= len(data):
                return name, val_start, "STRING", name

            # Try to infer type
            if val_start + 4 <= len(data):
                for fmt in ['<I', '>I']:
                    try:
                        val = struct.unpack(fmt, data[val_start:val_start+4])[0]
                        if 0 < val < 100000000:
                            return val, val_start + 4, "INT", name
                    except:
                        continue
            
            if val_start + 8 <= len(data):
                try:
                    val = struct.unpack('>d', data[val_start:val_start+8])[0]
                    if abs(val) < 1e15 and abs(val) > 1e-18:
                        return val, val_start + 8, "DOUBLE", name
                except:
                    pass
            
            end_idx = data.find(b'\x00', val_start)
            if end_idx == -1: end_idx = len(data)
            try:
                s_val = data[val_start:end_idx].decode('utf-8', errors='ignore').strip()
                return s_val if s_val else name, end_idx + 1, "STRING", name
            except:
                return name, val_start, "STRING", name

        return None, curr, "EOF", ""

if __name__ == "__main__":
    decoder = CreoProtocolDecoder()
    print("--- TEST 1: e0 INT ---")
    test_data = b'\xe0\x01_id\x00\x36\x00\x00\x00'
    print(decoder.decode_next_value(test_data, 0))
    print("\n--- TEST 2: Non-e0 INT ---")
    test_data = b'my_id\x00\x36\x00\x00\x00'
    print(decoder.decode_next_value(test_data, 0))
    print("\n--- TEST 3: Non-e0 STRING ---")
    test_data = b'my_name\x00hello\x00'
    print(decoder.decode_next_value(test_data, 0))
