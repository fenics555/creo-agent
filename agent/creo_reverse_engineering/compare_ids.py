import sys
import os
import re

# Fix paths
BASE_DIR = 'D:/AI/tools/agent'
SRC_DIR = os.path.join(BASE_DIR, 'creo_reverse_engineering', 'src')
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, SRC_DIR)

from plm_reader.creo_read import read
from creo_protocol_decoder import CreoProtocolDecoder

def run_comparison(file_path):
    data = read(file_path)
    decoder = CreoProtocolDecoder()
    
    # Manually defined offsets for the test file
    geom_depen_off = 15527
    geom_depen_len = 422
    feat_defs_off = 43416
    feat_defs_len = 1129

    print(f"--- Comparing IDs in {file_path} ---")

    # 1. Find body_ids in GeomDepen
    print("\n[GeomDepen]")
    depen_data = data[geom_depen_off : geom_depen_off + geom_depen_len]
    body_ids = []
    curr = 0
    while curr < len(depen_data):
        val, n_off, v_type, name = decoder.decode_next_value(depen_data, curr)
        if v_type in ["EOF", "NO_HEADER", "DECODE_FAILED"]:
            break
        if v_type == 'INT' and name == 'body_id':
            body_ids.append(val)
            print(f"  Found body_id: {val}")
        curr = n_off if n_off > curr else curr + 1
    
    if not body_ids:
        print("  (No body_id found in GeomDepen)")

    # 2. Find feat_ids in FeatDefs
    print("\n[FeatDefs]")
    feat_data = data[feat_defs_off : feat_defs_off + feat_defs_len]
    feat_ids = []
    
    pattern = re.compile(b'feat_defs_')
    matches = list(pattern.finditer(feat_data))
    
    for m in matches:
        start = m.end()
        sub_data = feat_data[start:start+20]
        digit_match = re.search(r'\d+', sub_data.decode('utf-8', errors='ignore'))
        if digit_match:
            f_id = int(digit_match.group())
            feat_ids.append(f_id)
            print(f"  Found feat_id from marker: {f_id}")
        else:
            print(f"  Found marker '{m.group().decode()}', but no ID following it.")

    if not feat_ids:
        print("  (No feat_id found in FeatDefs markers)")

    # 3. Compare
    print("\n[Comparison Result]")
    if not body_ids or not feat_ids:
        print("  Insufficient data for comparison.")
        return

    unique_body_ids = sorted(list(set(body_ids)))
    unique_feat_ids = sorted(list(set(feat_ids)))
    print(f"  Unique body_ids: {unique_body_ids}")
    print(f"  Unique feat_ids: {unique_feat_ids}")
    
    intersection = set(body_ids).intersection(set(feat_ids))
    if intersection:
        print(f"  ✅ MATCH FOUND! Intersecting IDs: {intersection}")
    else:
        print("  ❌ NO MATCH. The IDs do not overlap.")
        # Check for a potential offset or mapping
        if unique_body_ids and unique_feat_ids:
            diff = unique_body_ids[0] - unique_feat_ids[0]
            print(f"  Potential offset detected: {diff}")

if __name__ == "__main__":
    run_comparison('D:/AI/PROBA/models/00080-03.prt')
