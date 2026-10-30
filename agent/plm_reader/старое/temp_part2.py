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
