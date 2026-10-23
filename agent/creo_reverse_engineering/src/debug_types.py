import json
import os

JSON_PATH = r"D:\AI\tools\agent\creo_reverse_engineering\output\master_plm_graph.json"

def debug_plm_types():
    if not os.path.exists(JSON_PATH):
        print(f"Error: {JSON_PATH} not found.")
        return

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    nodes = data.get('nodes', {})
    types = set()
    for name, info in nodes.items():
        types.add(info.get('plm_type', 'Unknown'))

    print("--- Unique PLM Types Found ---")
    for t in sorted(types):
        print(f"- {t}")

if __name__ == "__main__":
    debug_plm_types()
