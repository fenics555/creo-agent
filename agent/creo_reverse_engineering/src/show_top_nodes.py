import json
import os

JSON_PATH = r"D:\AI\tools\agent\creo_reverse_engineering\output\master_plm_graph.json"

def show_top_nodes():
    if not os.path.exists(JSON_PATH):
        print("No JSON found.")
        return
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    nodes = data.get('nodes', {})
    edges = data.get('edges', [])

    out_degree = {}
    for edge in edges:
        src = edge['source']
        out_degree[src] = out_degree.get(src, 0) + 1

    sorted_roots = sorted(out_degree.items(), key=lambda x: x[1], reverse=True)

    print(f"--- TOP-LEVEL NODES BY CONNECTIVITY (Out-degree) ---\n")
    print(f"Showing top {min(5, len(sorted_roots))} nodes that control the most components:\n")

    for root, count in sorted_roots[:5]:
        print(f"[ROOT] {root} ({count} outgoing connections)")
        
        seen_targets = set()
        for edge in edges:
            if edge['source'] == root:
                target = edge['target']
                etype = edge['type']
                if (target, etype) not in seen_targets:
                    print(f"  └── ({etype}) ──▶ {target}")
                    seen_targets.add((target, etype))
        print()

if __name__ == "__main__":
    show_top_nodes()
