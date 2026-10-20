import struct

class CreoProtocolDecoder:
    """
    The 'Brain' of the parser. 
    Decodes the proprietary Creo binary protocol, specifically handling 
    the 'e0' type-indicator headers found in feature records.
    """
    
    def __init__(self):
        pass

    def decode_next_value(self, data: bytes, offset: int):
        """
        Searches for the next 'e0' header and decodes the value.
        Returns: (decoded_value, next_offset, value_type)
        """
        curr = offset
        
        while curr < len(data):
            # 1. Skip leading NULL bytes
            while curr < len(data) and data[curr] == 0:
                curr += 1
            
            if curr >= len(data):
                return None, curr, "EOF"

            # 2. Search for the next 'e0' header
            header_pos = data.find(b'\xe0', curr)
            if header_pos == -1:
                return None, curr, "NO_HEADER"
            
            # Update curr to the found header_pos
            curr = header_pos

            # 3. Validate Header Structure
            # Pattern: [Subtype/Len (1 byte)] + [e0 (1 byte)] + [Type (1 byte)]
            if curr < 1 or curr + 2 >= len(data):
                curr += 1
                continue

            try:
                type_byte = data[curr + 1]
                val_start = curr + 2
                
                # 4. Extract Value based on Type Byte
                if type_byte == 0x01: # INT
                    if val_start + 4 <= len(data):
                        for fmt in ['<I', '>I']:
                            try:
                                val = struct.unpack(fmt, data[val_start:val_start+4])[0]
                                if 0 < val < 10000000:
                                    return val, val_start + 4, "INT"
                            except:
                                continue
                
                elif type_byte == 0x02: # STRING
                    end_idx = data.find(b'\x00', val_start)
                    if end_idx == -1:
                        end_idx = len(data)
                    try:
                        s_val = data[val_start:end_idx].decode('utf-8', errors='ignore').strip()
                        if s_val:
                            return s_val, end_idx + 1, "STRING"
                    except:
                        pass

                elif type_byte == 0x03: # DOUBLE
                    if val_start + 8 <= len(data):
                        try:
                            val = struct.unpack('>d', data[val_start:val_start+8])[0]
                            if abs(val) < 1e15 and abs(val) > 1e-12:
                                return val, val_start + 8, "DOUBLE"
                        except:
                            pass

            except Exception:
                pass

            curr += 1
            
        return None, curr, "DECODE_FAILED"

if __name__ == "__main__":
    # Quick Test
    decoder = CreoProtocolDecoder()
    print("--- TEST 1: INT ---")
    test_data = b'\xf6\xe0\x01\x0a\x00\x00\x00'
    val, next_off, v_type = decoder.decode_next_value(test_data, 0)
    print(f"Result: {val} ({v_type}) | Next Offset: {next_off}")

    print("\n--- TEST 2: STRING ---")
    test_data = b'\xf6\xe0\x02Hello\x00'
    val, next_off, v_type = decoder.decode_next_value(test_data, 0)
    print(f"Result: {val} ({v_type}) | Next Offset: {next_off}")

    print("\n--- TEST 3: DOUBLE ---")
    import math
    pi_bytes = struct.pack('>d', math.pi)
    test_data = b'\xf6\xe0\x03' + pi_bytes
    val, next_off, v_type = decoder.decode_next_value(test_data, 0)
    print(f"Result: {val} ({v_type}) | Next Offset: {next_off}")
