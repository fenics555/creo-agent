

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
