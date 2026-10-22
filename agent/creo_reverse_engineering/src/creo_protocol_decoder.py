import struct

class CreoProtocolDecoder:
    def __init__(self, endian='<'):
        self.endian = endian

    def decode_next_value(self, data, curr):
        if curr + 2 > len(data):
            return None, curr, "EOF", None

        marker = data[curr:curr+2]
        v_type_id = marker[1]
        pos = curr + 2

        # Special case for Type 5 (BOM/List) - no name in the mock
        if v_type_id == 5:
            if pos + 4 > len(data):
                return None, curr, "DECODE_FAILED", None
            try:
                count = struct.unpack(f'{self.endian}I', data[pos:pos+4])[0]
                pos += 4
                vals = []
                for _ in range(count):
                    v_end = data.find(b'\x00', pos)
                    if v_end == -1:
                        break
                    vals.append(data[pos:v_end].decode('ascii', errors='ignore'))
                    pos = v_end + 1
                return vals, pos, "LIST", "BOM_LIST"
            except Exception:
                return None, curr, "DECODE_FAILED", None

        # Normal case: [Marker] [Name\x00] [Value]
        name_end = data.find(b'\x00', pos)
        if name_end == -1:
            return None, curr, "DECODE_FAILED", None
        
        name = data[pos:name_end].decode('ascii', errors='ignore')
        pos = name_end + 1

        if v_type_id == 1: # int
            if pos + 4 > len(data):
                return None, curr, "DECODE_FAILED", None
            try:
                val = struct.unpack(f'{self.endian}I', data[pos:pos+4])[0]
                return val, pos + 4, "int", name
            except Exception:
                return None, curr, "DECODE_FAILED", None

        elif v_type_id == 2: # string
            val_end = data.find(b'\x00', pos)
            if val_end == -1:
                return None, curr, "DECODE_FAILED", None
            val = data[pos:val_end].decode('ascii', errors='ignore')
            return val, val_end + 1, "string", name

        elif v_type_id == 3: # double
            if pos + 8 > len(data):
                return None, curr, "DECODE_FAILED", None
            try:
                val = struct.unpack(f'{self.endian}d', data[pos:pos+8])[0]
                return val, pos + 8, "double", name
            except Exception:
                return None, curr, "DECODE_FAILED", None
        
        return None, curr, "DECODE_FAILED", None

