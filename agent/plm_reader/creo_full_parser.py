import sys
import os

# Add plm_reader to sys.path
sys.path.append(r'D:\AI\tools\agent\plm_reader')

import creo_read
import creo_tree_reader

models = [
    r'D:\AI\PROBA\test_family.prt',
    r'D:\AI\PROBA\models\00080-03.prt',
    r'D:\AI\PROBA\models\00080-00.asm',
    r'D:\AI\PROBA\models\base-with-4holes.prt'
]

for model in models:
    if not os.path.exists(model):
        print(f"MISSING: {model}")
        continue
    
    print(f"--- Testing: {os.path.basename(model)} ---")
    try:
        with open(model, 'rb') as f:
            data = f.read()
        
        # Check tree directly
        tree = creo_tree_reader.get_tree_dict(data)
        print(f"Tree Sections Found: {len(tree.get('sections', []))}")
        for s in tree.get('sections', []):
            stype = s.get('type', 'unknown_type')
            sname = s.get('name', 'N/A')
            print(f"  [{stype}] Name: {sname} (len: {s.get('len')})")
            
        result = creo_read.get_structural_data(data)
        print(f"Result: {result}")
    except Exception as e:
        print(f"ERROR: {e}")
    print()
