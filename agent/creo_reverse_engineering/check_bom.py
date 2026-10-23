import json
import sys

def check_targets(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        edges = json.load(f)
    
    bom_targets = [e['target'] for e in edges if e['type'] == 'bom_component']
    
    sys.stdout.buffer.write(f"Total BOM components: {len(bom_targets)}\n".encode('utf-8'))
    sys.stdout.buffer.write(b"First 10 targets:\n")
    for t in bom_targets[:10]:
        sys.stdout.buffer.write(f"  {repr(t)}\n".encode('utf-8'))

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        check_targets(sys.argv[1])
    else:
        print("Usage: python script.py <path_to_json>")
