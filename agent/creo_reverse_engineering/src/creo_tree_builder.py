import struct
import re
from creo_protocol_decoder import CreoProtocolDecoder

class CreoTreeBuilder:
    """
    Builds the feature tree by surgically extracting parent-child relationships 
    using identified key-value patterns and the Protocol Decoder.
    """
    def __init__(self, file_path):
        self.file_path = file_path
        self.features = {}  # id -> {offset, data}
        self.adj = {}       # parent_id -> [child_ids]
        self.all_ids = set()
        self.decoder = CreoProtocolDecoder()
        # Precise keys for relationship extraction
        self.rel_keys = [
            b'sub_feat_id',
            b'parent_id',
            b'ref_id',
            b'next'
        ]

    def load_features(self, toc_offset):
        """Loads all features from the FeatDefs section by finding feat_defs_ patterns."""
        print(f"Loading features from {hex(toc_offset)}...")
        try:
            with open(self.file_path, 'rb') as f:
                f.seek(toc_offset)
                data = f.read()
                
                pattern = re.compile(b'feat_defs_')
                matches = list(pattern.finditer(data))
                print(f"Found {len(matches)} feat_defs_ markers.")
                
                count = 0
                for i, match in enumerate(matches):
                    start_idx = match.start()
                    
                    if i + 1 < len(matches):
                        end_idx = matches[i+1].start()
                    else:
                        end_idx = len(data)
                    
                    record = data[start_idx:end_idx]
                    
                    # Extract ID: feat_defs_1234 -> 1234
                    id_match = re.search(b'feat_defs_([a-zA-Z0-9_]+)', record)
                    if id_match:
                        raw_id = id_match.group(1).decode('utf-8')
                        # We want the numeric part as the primary ID to match the geom extractor
                        numeric_id_match = re.search(r'\d+', raw_id)
                        feat_id = numeric_id_match.group() if numeric_id_match else raw_id
                        
                        abs_offset = toc_offset + start_idx
                        
                        self.features[feat_id] = {
                            'offset': abs_offset,
                            'data': record,
                            'raw_id': raw_id
                        }
                        self.all_ids.add(feat_id)
                        count += 1
                
                print(f"Successfully loaded {count} features.")
        except Exception as e:
            print(f"Error loading features: {e}")

    def build_tree(self):
        """Parses records to find parent-child relationships using Key-Value extraction."""
        print("Building tree (Protocol Decoder mode)...")
        for fid in self.all_ids:
            if fid not in self.adj:
                self.adj[fid] = []

        for feat_id, info in self.features.items():
            data = info['data']
            
            for key in self.rel_keys:
                idx = data.find(key)
                if idx != -1:
                    # The value starts after the key and its null terminator
                    val_start = idx + len(key)
                    # Skip null terminator
                    while val_start < len(data) and data[val_start] == 0:
                        val_start += 1
                    
                    # Use the decoder to get the value following the key
                    val, next_off, v_type = self.decoder.decode_next_value(data, val_start)
                    
                    # Only consider numeric (INT) values as potential feature IDs
                    if v_type == 'INT':
                        target_id = str(val)
                        if target_id != feat_id:
                            # Check if the target_id is actually a known feature
                            if target_id in self.all_ids:
                                if target_id not in self.adj.get(feat_id, []):
                                    if feat_id not in self.adj: self.adj[feat_id] = []
                                    self.adj[feat_id].append(target_id)

    def print_tree(self, node=None, depth=0, visited=None):
        if visited is None:
            visited = set()
        
        if node is None:
            all_children = set()
            for children in self.adj.values():
                for c in children:
                    all_children.add(c)
            
            roots = [i for i in self.all_ids if i not in all_children]
            for root in sorted(roots):
                self.print_tree(root, 0, visited)
            return
        
        if node in visited:
            print("  " * depth + f"{node} (cycle!)")
            return
        
        visited.add(node)
        print("  " * depth + f"|- {node}")
        
        if node in self.adj:
            for child in sorted(self.adj[node]):
                self.print_tree(child, depth + 1, visited)

if __name__ == "__main__":
    # Test local logic
    test_file = r"D:\AI\PROBA\models\23-1017GRI 2кап чистовой BDF 5 1_2''\23-1017gri-02.prt.1"
    # Corrected TOC offset from test_toc.py
    toc_offset = 719903 
    
    builder = CreoTreeBuilder(test_file)
    builder.load_features(toc_offset)
    builder.build_tree()
    
    print("\n--- RECONSTRUCTED FEATURE TREE (KV MODE) ---")
    builder.print_tree()
