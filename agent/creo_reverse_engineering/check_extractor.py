import sys
import os

# Ensure paths are correct
sys.path.append(r'D:\AI\tools\agent')
sys.path.append(r'D:\AI\tools\agent\creo_reverse_engineering\src')

try:
    from creo_geom_extractor import scan_all_features
    print("SUCCESS: Import creo_geom_extractor")
except ImportError as e:
    print(f"FAILURE: Import creo_geom_extractor: {e}")
    sys.exit(1)

test_file = r"D:\AI\PROBA\models\00080-03.prt"
if not os.path.exists(test_file):
    print(f"FAILURE: Test file not found: {test_file}")
    sys.exit(1)

print(f"Running scan on {test_file}...")
feats = scan_all_features(test_file)
print(f"Found {len(feats)} features.")

for i, f in enumerate(feats):
    out = f"\n--- Feature {i} ---\n"
    out += f"ID: {repr(f.get('id'))} | BodyID: {repr(f.get('body_id'))}\n"
    out += "Params:\n"
    for p in f.get('params', []):
        out += f"  - {repr(p['name'])}: {repr(p['value'])} ({repr(p['type'])})\n"
    sys.stdout.buffer.write(out.encode('utf-8'))
