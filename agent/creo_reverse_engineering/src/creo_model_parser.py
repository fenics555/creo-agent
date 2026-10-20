import os
import json
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'plm_reader'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
try:
    from creo_read import parse_toc, read
    from creo_geom_extractor import scan_all_features
    from creo_tree_builder import CreoTreeBuilder
    from creo_feature_classifier import CreoFeatureClassifier
    from creo_protocol_decoder import CreoProtocolDecoder
except ImportError as e:
    print(f"Error: {e}"); sys.exit(1)
class CreoModelParser:
    def __init__(self, file_path):
        self.file_path = file_path
        self.raw_data = read(file_path)
        self.toc = {}
        self.tree = {}
        self.features_list = []
        self.classifier = CreoFeatureClassifier()
        self.decoder = CreoProtocolDecoder()
        self.model_data = {"file": file_path, "features": []}
    def parse(self):
        print(f"--- Parse: {self.file_path} ---")
        self.toc = parse_toc(self.raw_data)
        feat_off = self.toc.get('FeatDefs', (0, 0))[0]
        tb = CreoTreeBuilder(self.file_path)
        if hasattr(tb, 'load_features'): tb.load_features(feat_off)
        tb.build_tree()
        self.tree = tb.adj
        self.all_ids = tb.all_ids
        self.features_list = scan_all_features(self.file_path)
        self._map_geometry()
        self._integrate()
        return self.model_data
    def _map_geometry(self):
        if 'GeomDepen' not in self.toc or 'Geomlists' not in self.toc: return
        d_off, d_len = self.toc['GeomDepen']
        depen_data = self.raw_data[d_off : d_off + d_len]
        self.geom_map = {}
        curr = 0
        while curr < len(depen_data):
            v1, n_off, t1 = self.decoder.decode_next_value(depen_data, curr)
            if t1 == 'INT':
                v2, n_off2, t2 = self.decoder.decode_next_value(depen_data, n_off)
                if t2 == 'INT':
                    self.geom_map.setdefault(str(v1), []).append(v2)
                    curr = n_off2; continue
            curr += 1
    def _integrate(self):
        fm = {f['id']: f for f in self.features_list}
        integrated = []
        for fid in sorted(self.all_ids, key=lambda x: str(x)):
            if fid in fm:
                f = fm[fid]
                f['type_info'] = self.classifier.classify(f['record'])
                integrated.append({"id": fid, "type": f['type_info']['type'], "params": f['params'], "geom_indices": f.get('geom_indices', [])})
            else:
                integrated.append({"id": fid, "type": "unknown", "params": []})
        self.model_data["features"] = integrated
    def to_json(self, path):
        with open(path, 'w', encoding='utf-8') as f: json.dump(self.model_data, f, indent=4, ensure_ascii=False)
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        p = CreoModelParser(sys.argv[1]); p.parse(); p.to_json("output_model.json")

import os
import json
import sys

# Add paths to sys.path to ensure modules can be found
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'plm_reader'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from creo_read import parse_toc, read
    from creo_geom_extractor import scan_all_features
    from creo_tree_builder import CreoTreeBuilder
    from creo_feature_classifier import CreoFeatureClassifier
except ImportError as e:
    print(f"CRITICAL ERROR: Failed to import modules. Check sys.path. Error: {e}")
    sys.exit(1)

class CreoModelParser:
    """
    The Master Integrator for CR-Toolkit.
    Coordinates TOC, Tree, Geometry, and Classification into a unified semantic model.
    """
    def __init__(self, file_path: str):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Model file not found: {file_path}")
        
        self.file_path = file_path
        self.raw_data = read(file_path)
        self.toc = {}
        self.tree = {}
        self.features_list = []
        self.classifier = CreoFeatureClassifier()
        self.model_data = {
            "file": file_path,
            "features": []
        }

    def parse(self):
        print(f"--- Starting Full Model Parse: {self.file_path} ---")
        
        # 1. Parse TOC
        print("[1/4] Parsing TOC...")
        self.toc = parse_toc(self.raw_data)
        if not self.toc:
            raise Exception("Failed to parse TOC. Cannot proceed.")
        print(f"      Found {len(self.toc)} TOC entries.")

        # 2. Build Feature Tree
        print("[2/4] Reconstructing Feature Tree...")
        feat_defs_offset = 0
        if 'FeatDefs' in self.toc:
            feat_defs_offset = self.toc['FeatDefs'][0]
            print(f"      FeatDefs offset: {hex(feat_defs_offset)}")
        else:
            print("      [WARNING] FeatDefs not in TOC. Falling back to scan.")

        tree_builder = CreoTreeBuilder(self.file_path)
        if hasattr(tree_builder, 'load_features'):
             tree_builder.load_features(feat_defs_offset)
        
        tree_builder.build_tree()
        self.tree = tree_builder.adj
        self.all_ids = tree_builder.all_ids
        print(f"      Tree reconstructed with {len(self.all_ids)} IDs.")

        # 3. Extract Features and Parameters (The "Scan")
        print("[3/4] Extracting Features & Parameters...")
        self.features_list = scan_all_features(self.file_path)
        print(f"      Extracted {len(self.features_list)} feature records.")

        # 4. Semantic Integration (The "Brain")
        print("[4/4] Performing Semantic Integration...")
        self._integrate()

        print("--- Parse Completed Successfully ---")
        return self.model_data

    def _integrate(self):
        """
        Links the tree, the parameters, and the classification.
        """
        feat_map = {f['id']: f for f in self.features_list}
        integrated_features = []
        
        for fid in sorted(self.all_ids, key=lambda x: str(x)):
            if fid in feat_map:
                f_data = feat_map[fid]
                f_data['type_info'] = self.classifier.classify(f_data['record'])
                
                node = {
                    "id": fid,
                    "type": f_data['type_info']['type'],
                    "params": f_data['params'],
                    "children": [] 
                }
                integrated_features.append(node)
            else:
                integrated_features.append({
                    "id": fid,
                    "type": "unknown",
                    "params": [],
                    "note": "Not found in scan"
                })

        self.model_data["features"] = integrated_features

    def to_json(self, output_path: str):
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.model_data, f, indent=4, ensure_ascii=False)
        print(f"Model exported to: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("USAGE: python creo_model_parser.py <path_to_prt_file>")
    else:
        parser = CreoModelParser(sys.argv[1])
        data = parser.parse()
        parser.to_json("output_model.json")
