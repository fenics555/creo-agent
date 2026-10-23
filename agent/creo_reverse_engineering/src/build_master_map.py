import json
import os
import glob
from collections import defaultdict

INPUT_DIR = r"D:\AI\tools\agent\creo_reverse_engineering\output\raw_json"
OUTPUT_FILE = r"D:\AI\tools\agent\creo_reverse_engineering\output\master_plm_graph.json"

def build_master_map():
    print(f"[*] Loading JSON files from {INPUT_DIR}...")
    
    # master_nodes: model_name -> { 'type': ..., 'params': { ... } }
    master_nodes = {}
    # master_edges: list of { 'source': ..., 'target': ..., 'type': ..., 'metadata': { ... } }
    master_edges = []
    
    json_files = glob.glob(os.path.join(INPUT_DIR, "*.json"))
    print(f"[*] Found {len(json_files)} JSON files.")

    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            model_name = data.get('model_name')
            if not model_name:
                continue

            # 1. Update/Create Node
            if model_name not in master_nodes:
                master_nodes[model_name] = {
                    'plm_type': data.get('plm_type', 'Unknown'),
                    'params': {}
                }
            
            # Merge parameters (if found in multiple files for same model)
            master_nodes[model_name]['params'].update(data.get('params', {}))

            # 2. Add Edges
            for edge in data.get('edges', []):
                # We want to avoid self-loops unless they are intentional
                # But in Creo, sometimes a part refers to itself in some way.
                # For the Master Map, let's just add them.
                master_edges.append(edge)

        except Exception as e:
            print(f"  [!] Error reading {json_file}: {e}")

    # 3. Post-processing: Deduplicate Edges
    # An edge is defined by (source, target, type)
    unique_edges = []
    seen_edges = set()

    for edge in master_edges:
        # Create a signature for the edge to identify duplicates
        # We include metadata in the signature if it's important, 
        # but for a master map, we usually want one edge between two entities of a type.
        edge_sig = (edge['source'], edge['target'], edge['type'])
        
        if edge_sig not in seen_edges:
            unique_edges.append(edge)
            seen_edges.add(edge_sig)

    # 4. Construct Final Graph
    master_graph = {
        'metadata': {
            'total_nodes': len(master_nodes),
            'total_edges': len(unique_edges),
            'source_files': len(json_files)
        },
        'nodes': master_nodes,
        'edges': unique_edges
    }

    print(f"[*] Writing master graph to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(master_graph, f, ensure_ascii=False, indent=4)

    print(f"[+] Success! Master map built with {len(master_nodes)} nodes and {len(unique_edges)} edges.")

if __name__ == "__main__":
    build_master_map()
