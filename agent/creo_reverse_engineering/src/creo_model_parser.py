import os
import json
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'plm_reader'))
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
        self.geom_map = {} # feat_id -> list of geom_indices

    def parse(self):
        print(f"--- Parse: {self.file_path} ---")
        self.toc = parse_toc(self.raw_data)
        if not self.toc: raise Exception("TOC Error")
        
        # 1. Build Tree & Load Features
        feat_off = self.toc.get('FeatDefs', (0, 0))[0]
        tb = CreoTreeBuilder(self.file_path)
        if hasattr(tb, 'load_features'): tb.load_features(feat_off)
        tb.build_tree()
        self.tree = tb.adj
        self.all_ids = tb.all_ids
        self.features_list = scan_all_features(self.file_path)
        
        # 2. Mapping Geometry Dependencies
        self._map_geometry()
        
        # 3. Integration
        self._integrate()
        return self.model_data

    def _map_geometry(self):
        if 'GeomDepen' not in self.toc or 'Geomlists' not in self.toc: 
            print("GeomDepen or Geomlists missing in TOC")
            return
            
        d_off, d_len = self.toc['GeomDepen']
        depen_data = self.raw_data[d_off : d_off + d_len]
        
        print(f"Mapping geometry from GeomDepen ({d_off}:{d_len})...")
        
        curr = 0
        current_dep = {}
        
        while curr < len(depen_data):
            val, n_off, v_type, name = self.decoder.decode_next_value(depen_data, curr)
            
            if v_type in ["EOF", "NO_HEADER"]:
                break
                
            if v_type == "HEADER":
                if current_dep:
                    self._process_dependency_block(current_dep)
                    current_dep = {}
                curr = n_off
                continue

            if name:
                # If it's a known ID field, use it as the key
                if name in ['body_id', 'feat_id', 'parent_id']:
                    if 'feat_id' in current_dep:
                        self._process_dependency_block(current_dep)
                        current_dep = {}
                    current_dep['feat_id'] = val
                else:
                    current_dep[name] = val
                curr = n_off
            else:
                curr += 1

        if current_dep:
            self._process_dependency_block(current_dep)

    def _process_dependency_block(self, dep_block):
        fid = dep_block.get('feat_id')
        if fid is None:
            return
            
        fid_str = str(fid)
        if fid_str not in self.geom_map:
            self.geom_map[fid_str] = []
            
        # Link geom_index or size (as proxy)
        if 'size' in dep_block:
            try:
                size = int(dep_block['size'])
                for i in range(size):
                    self.geom_map[fid_str].append(i)
            except: pass
        
        if 'geom_index' in dep_block:
            try:
                self.geom_map[fid_str].append(dep_block['geom_index'])
            except: pass

    def _integrate(self):
        fm = {str(f['id']): f for f in self.features_list}
        integrated = []
        for fid in sorted(self.all_ids, key=lambda x: str(x)):
            fid_str = str(fid)
            if fid_str in fm:
                f = fm[fid_str]
                f['type_info'] = self.classifier.classify(f['record'])
                
                # Apply the mapped geometry indices
                geom_indices = self.geom_map.get(fid_str, [])
                
                integrated.append({
                    "id": fid, 
                    "type": f['type_info']['type'], 
                    "params": f['params'], 
                    "geom_indices": geom_indices
                })
            else:
                integrated.append({"id": fid, "type": "unknown", "params": []})
        self.model_data['features'] = integrated

    def to_json(self, path):
        with open(path, 'w', encoding='utf-8') as f: 
            json.dump(self.model_data, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        p = CreoModelParser(sys.argv[1])
        p.parse()
        p.to_json("output_model.json")
