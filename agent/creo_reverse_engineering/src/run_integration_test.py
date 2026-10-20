import sys
import os
import json

# Настройка путей
sys.path.append('D:/AI/tools/agent')
sys.path.append('D:/AI/tools/agent/creo_reverse_engineering/src')

from creo_geom_extractor import scan_all_features
from creo_mapping_utils import build_feat_body_map

def run_test(file_path):
    print(f"=== INTEGRATION TEST: {file_path} ===")
    
    # 1. Извлечение признаков
    features = scan_all_features(file_path)
    if not features:
        print("No features found. Aborting.")
        return

    print(f"Extracted {len(features)} features.")

    # 2. Построение маппинга
    mapping = build_feat_body_map(features)
    print(f"Built mapping with {len(mapping)} body_id -> feat_id links.")

    # 3. Демонстрация работы маппинга
    # Ищем пример body_id в извлеченных признаках
    sample_feat = next((f for f in features if f['body_id'] is not None), None)
    
    if sample_feat:
        bid = sample_feat['body_id']
        fid = mapping.get(bid)
        print(f"\n[DEMO] Found sample: BodyID={bid} -> mapped to FeatID={fid}")
        
        # Проверка обратной связи
        if fid:
            original_feat = next((f for f in features if f['id'] == fid), None)
            if original_feat:
                print(f"    Verified: Feat {fid} actually has BodyID {original_feat['body_id']}")
    else:
        print("\n[DEMO] No body_id found in any feature for this file.")

if __name__ == "__main__":
    test_file = r"D:\AI\PROBA\models\00080-03.prt"
    if os.path.exists(test_file):
        run_test(test_file)
    else:
        print(f"File not found: {test_file}")
