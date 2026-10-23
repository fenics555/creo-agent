import json
import os

JSON_PATH = r"D:\AI\tools\agent\creo_reverse_engineering\output\master_plm_graph.json"

def visualize_top_level():
    if not os.path.exists(JSON_PATH):
        print(f"Error: {JSON_PATH} not found.")
        return

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    nodes = data.get('nodes', {})
    edges = data.get('edges', [])

    # 1. Находим "корневые" узлы (Assembly или Master)
    roots = []
    for name, info in nodes.items():
        p_type = info.get('plm_type', '').upper()
        if 'ASSEM' in p_type or 'MASTER' in p_type:
            roots.append(name)

    if not roots:
        print("No root nodes (Assembly/Master) found.")
        return

    print(f"--- TOP-LEVEL HIERARCHY (Found {len(roots)} roots) ---\n")

    # 2. Для каждого корня ищем прямых детей
    for root in roots:
        root_type = nodes[root].get('plm_type', 'Unknown')
        print(f"ROOT: {root} [{root_type}]")
        
        # Ищем все исходящие связи от этого корня
        children_found = False
        # Чтобы не было дублей, если один и тот же компонент подключен разными способами
        seen_children = set()

        for edge in edges:
            if edge['source'] == root:
                target = edge['target']
                e_type = edge['type']
                
                child_type = nodes.get(target, {}).get('plm_type', 'Unknown')
                
                # Создаем уникальный ключ для отображения
                child_key = (target, e_type)
                if child_key not in seen_children:
                    print(f"  └── ({e_type}) ──▶ {target} [{child_type}]")
                    seen_children.add(child_key)
                    children_found = True
        
        if not children_found:
            print("  └── (No direct children found)")
        print()

if __name__ == "__main__":
    visualize_top_level()
