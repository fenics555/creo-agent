import struct
import re

class CreoFeatureClassifier:
    """
    Classifies Creo features by surgical Key-Value extraction.
    Instead of searching a window, it looks for specific attribute keys 
    (type, ft_type, AE_Type) and extracts the value following them.
    """
    
    # Mapping of raw byte codes to human-readable names
    TYPE_MAP = {
        0x01: "UNKNOWN_01",
        0x02: "SKETCH",
        0x03: "DATUM_PLANE",
        0x05: "EXTRUDE",
        0x06: "REVOLVE",
        0x07: "ROUND",
        0x08: "HOLE",
        0x80: "FEATURE_GROUP",
    }

    def __init__(self):
        # Priorities: AE_ prefix keys first, then standard keys
        self.search_patterns = [
            b'AE_Type\x00',
            b'AE_Sub_Type\x00',
            b'type\x00',
            b'ft_type\x00',
            b'sub_type\x00'
        ]
        # Creo often uses these prefixes before a value
        self.value_prefixes = [b'\xe0\x01', b'\xe0\x02', b'\xe3\x02']

    def _sanitize_type(self, type_str: str) -> str:
        """Removes non-printable characters and cleans up the type string."""
        # Remove non-printable characters
        sanitized = "".join(c for c in type_str if c.isprintable())
        # If it's empty or too short, return UNKNOWN
        if not sanitized or len(sanitized) < 2:
            return "UNKNOWN"
        return sanitized

    def _get_value_after_key(self, record: bytes, key: bytes):
        """Extracts the value immediately following a specific key."""
        idx = record.find(key)
        if idx == -1:
            return None, None
        
        val_start = idx + len(key)
        
        # 1. Skip any binary metadata prefixes
        for prefix in self.value_prefixes:
            if record[val_start:val_start+len(prefix)] == prefix:
                val_start += len(prefix)
                break
        
        if val_start >= len(record):
            return None, None

        # 2. Determine if the value is a String or a Code
        # Try reading as a Null-terminated string first
        end_idx = record.find(b'\x00', val_start)
        if end_idx != -1 and end_idx < val_start + 64:
            try:
                str_val = record[val_start:end_idx].decode('utf-8', errors='ignore').strip()
                if str_val:
                    return str_val, 0
            except:
                pass

        # 3. If not a string, try reading as a single byte (code)
        first_byte = record[val_start]
        if first_byte < 0x20 or first_byte >= 0x80:
            return self.TYPE_MAP.get(first_byte, f"CODE_{first_byte:02X}"), first_byte

        # 4. Final fallback: try 4-byte integer
        if val_start + 4 <= len(record):
            for fmt in ['<I', '>I']:
                try:
                    int_val = struct.unpack(fmt, record[val_start:val_start+4])[0]
                    if 0 < int_val < 1000000:
                        return f"CODE_{int_val:X}", int_val
                except:
                    continue

        return None, None

    def classify(self, record: bytes) -> dict:
        """
        Surgically classifies a feature using the best available key.
        """
        for pattern in self.search_patterns:
            val_str, val_raw = self._get_value_after_key(record, pattern)
            if val_str:
                return {"type": self._sanitize_type(val_str), "type_raw": val_raw}
        
        return {"type": "unknown", "type_raw": 0}

if __name__ == "__main__":
    # Test Suite
    classifier = CreoFeatureClassifier()
    
    print("--- TEST 1: Standard Byte Code ---")
    rec1 = b"feat_defs_123...type\x00\x05"
    print(f"Result: {classifier.classify(rec1)}")

    print("\n--- TEST 2: Standard String ---")
    rec2 = b"feat_defs_456...type\x00extrude\x00"
    print(f"Result: {classifier.classify(rec2)}")

    print("\n--- TEST 3: AE_ Prefix (Attribute) ---")
    rec3 = b"feat_defs_789...AE_Type\x00\x06"
    print(f"Result: {classifier.classify(rec3)}")

    print("\n--- TEST 4: AE_ Prefix (String) ---")
    rec4 = b"feat_defs_101...AE_Type\x00REVOLVE\x00"
    print(f"Result: {classifier.classify(rec4)}")

    print("\n--- TEST 5: Dirty Data (Noise) ---")
    rec5 = b"feat_defs_999...some_random_garbage_data_without_keys"
    print(f"Result: {classifier.classify(rec5)}")

    print("\n--- TEST 6: Garbage with Control Characters ---")
    rec6 = b"feat_defs_999...type\x00\x01\x12\x01attr\x00"
    print(f"Result: {classifier.classify(rec6)}")
