import sys
import os
import json
import struct
import re

# Correct Path Setup
ROOT = r'D:\AI\tools\agent\creo_reverse_engineering'
SRC = os.path.join(ROOT, 'src')
sys.path.insert(0, ROOT)
sys.path.insert(0, SRC)

try:
    from creo_protocol_decoder import CreoProtocolDecoder
except ImportError as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

def parse_toc(data):
    toc = {}
    toc_start = data.find(b'#UGC_TOC')
    if toc_start == -1:
        return toc
    
    pattern = re.compile(rb'#?([\w]+):\s*([0-9A-Fa-f]+)\s+([0-9A-Fa-f]+)')
    
    for match in pattern.finditer(data[toc_start:]):
        name = match.group(1).decode('ascii')
        offset = int(match.group(2), 16)
        size = int(match.group(3), 16)
        toc[name] = {'offset': offset, 'size': size}
    
    return toc

def parse_mapping_table(file_path):
    """
    Parses the Creo mapping table and returns a dictionary with metadata and results.
    Returns: {'metadata': {'parsed_at': str, 'status': str, 'detected_role': str}, 'mapping_table': list}
    """
    file_name = os.path.basename(file_path)
    
    with open(file_path, 'rb') as f:
        data = f.read()

    toc = parse_toc(data)
    
    # Initialize result structure
    result = {
        "metadata": {
            "parsed_at": file_name,
            "status": "failed",
            "detected_role": "Unknown"
        },
        "mapping_table": []
    }

    if not toc:
        result["metadata"]["status"] = "error: TOC not found"
        return result

    if 'setup_data' not in toc:
        result["metadata"]["status"] = "error: setup_data not found"
        return result

    setup_off = toc['setup_data']['offset']
    setup_sz = toc['setup_data']['size']
    setup_data = data[setup_off : setup_off + setup_sz]

    key = b'id_map_info_ptr\x00'
    idx = setup_data.find(key)
    if idx == -1:
        result["metadata"]["status"] = "error: id_map_info_ptr not found"
        return result

    ptr_pos = idx + len(key)
    if ptr_pos + 2 > len(setup_data):
        result["metadata"]["status"] = "error: id_map_info_ptr truncated"
        return result
    
    rel_offset = struct.unpack('<H', setup_data[ptr_pos:ptr_pos+2])[0]
    table_start = setup_off + rel_offset
    
    decoder = CreoProtocolDecoder(endian='<')
    mapping_results = []
    
    curr = table_start
    while curr < len(data):
        val, next_off, v_type, name = decoder.decode_next_value(data, curr)
        if v_type == "EOF" or next_off == curr:
            break
            
        mapping_results.append({
            "name": name,
            "value": val,
            "type": v_type
        })
        curr = next_off
    
    # Determine Role Heuristically
    # If we found specific parameters (Mass, Vol, etc.), it's likely a Part.
    # If the table is empty but the file exists, we assume it's an Assembly/Container for this mock.
    has_params = any("Param" in item["name"] or "Fixture" in item["name"] for item in mapping_results)
    
    if mapping_results:
        result["metadata"]["detected_role"] = "Деталь (Part)" if has_params else "Unknown"
        result["metadata"]["status"] = "success"
    else:
        result["metadata"]["detected_role"] = "Сборка (Assembly)"
        result["metadata"]["status"] = "success" # Success, but empty table is normal for assemblies

    result["mapping_table"] = mapping_results
    return result

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("USAGE: python creo_mapping_table_parser.py <input_bin> <output_json>")
        sys.exit(1)

    input_bin = sys.argv[1]
    output_json = sys.argv[2]

    try:
        data = parse_mapping_table(input_bin)
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Successfully parsed. Status: {data['metadata']['status']}. Output: {output_json}")
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
