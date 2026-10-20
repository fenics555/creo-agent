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
    def parse(self):
        print(f"--- Parse: {self.file_path} ---")
        self.toc = parse_toc(self.raw_data)
        if not self.toc: raise Exception("TOC Error")
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
        self.model_data['features'] = integrated
    def to_json(self, path):
        with open(path, 'w', encoding='utf-8') as f: json.dump(self.model_data, f, indent=4, ensure_ascii=False)
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        p = CreoModelParser(sys.argv[1]); p.parse(); p.to_json("output_model.json")
