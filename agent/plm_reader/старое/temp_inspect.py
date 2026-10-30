import sys
import os

# Добавляем пути
sys.path.append('D:/AI/tools/agent/plm_reader')
sys.path.append('D:/AI/tools/agent/creo_reverse_engineering/src')

# Теперь импортируем напрямую из папок в sys.path
try:
    import creo_read
    from creo_geom_extractor import scan_all_features
    print("Imports successful.")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

def inspect_params(file_path):
    feats = scan_all_features(file_path)
    if not feats:
        print("No features found.")
        return
    
    feat = feats[0]
    print(f"\n=== Inspection of Feature {feat['id']} ===")
    print(f"BodyID: {feat['body_id']}")
    print(f"Total Params: {len(feat['params'])}")
    print("-" * 30)
    for p in feat['params'][:50]: # Show first 50
        print(f"{p['name']:<20} | {repr(p['value']):<20} | {p['type']}")

if __name__ == "__main__":
    test_file = r"D:\AI\PROBA\models\00080-03.prt"
    if os.path.exists(test_file):
        inspect_params(test_file)
    else:
        print(f"File not found: {test_file}")

import sys
sys.path.append('D:/AI/tools/agent/plm_reader')
sys.path.append('D:/AI/tools/agent/creo_reverse_engineering/src')

from creo_geom_extractor import scan_all_features

def inspect_params(file_path):
    feats = scan_all_features(file_path)
    if not feats:
        return
    
    feat = feats[0]
    print(f"\n=== Inspection of Feature {feat['id']} ===")
    print(f"BodyID: {feat['body_id']}")
    print(f"Total Params: {len(feat['params'])}")
    print("-" * 30)
    for p in feat['params'][:30]: # Show first 30
        print(f"{p['name']:<20} | {repr(p['value']):<20} | {p['type']}")

if __name__ == "__main__":
    inspect_params(r"D:\AI\PROBA\models\00080-03.prt")
