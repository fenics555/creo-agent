import json
import os

JSON_PATH = r"D:\AI\tools\agent\creo_reverse_engineering\output\master_plm_graph.json"

def run():
    if not os.path.exists(JSON_PATH):
        print("No JSON found.")
        return
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    nodes = data.get('nodes', {})
    edges = data.get('edges', [])
    
    roots = [n for n in nodes if n.lower().endswith(('.asm', '.asm.1', '.mstr', '.mstr.1'))]
    
    print(f"Found {len(roots)} roots. Printing top 5:")
    for root in roots[:5]:
        print(f"\nROOT: {root}")
        seen = set()
        for e in edges:
            if e['source'] == root:
                t, et = e['target'], e['type']
                if (t, et) not in seen:
                    print(f"  └── ({et}) -> {t}")
                    seen.add((t, et))

if __name__ == "__main__":
    run()
