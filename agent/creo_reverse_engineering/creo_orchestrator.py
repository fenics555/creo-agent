import sys
import os
import json
from datetime import datetime

# Add paths to sys.path to ensure modules can be found
sys.path.insert(0, r'D:\AI\tools\agent\plm_reader')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    import creo_read
    from creo_geom_extractor import scan_all_features
    from creo_tree_builder import CreoTreeBuilder
    from creo_feature_classifier import CreoFeatureClassifier
except ImportError as e:
    print(f"CRITICAL ERROR: Failed to import modules. Check sys.path. Error: {e}")
    sys.exit(1)

class CreoOrchestrator:
    """
    The Master Controller for Creo Reverse Engineering.
    Coordinates TOC parsing, feature extraction, tree building, and classification.
    """
    def __init__(self, target_file):
        self.target_file = target_file
        self.toc = {}
        self.features_data = []
        self.tree_adj = {}
        self.all_ids = set()
        self.classifier = CreoFeatureClassifier()

    def execute(self):
        print(f"{'='*60}")
        print(f"CREO REVERSE ENGINEERING ORCHESTRATOR")
        print(f"Target: {self.target_file}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")

        # 1. Read and Parse TOC
        try:
            print("[1/4] Parsing TOC...")
            with open(self.target_file, 'rb') as f:
                raw_data = f.read()
            self.toc = creo_read.parse_toc(raw_data)
            if not self.toc:
                print("ERROR: Failed to parse TOC.")
                return
            print(f"      Found {len(self.toc)} TOC entries.")
        except Exception as e:
            print(f"ERROR reading file: {e}")
            return

        # 2. Extract Features and Parameters
        try:
            print("[2/4] Extracting Features & Parameters...")
            self.features_data = scan_all_features(self.target_file)
            print(f"      Extracted {len(self.features_data)} features.")
        except Exception as e:
            print(f"ERROR during extraction: {e}")
            return

        # 3. Classify Features
        try:
            print("[3/4] Classifying Features...")
            for feat in self.features_data:
                feat['type_info'] = self.classifier.classify(feat['record'])
            print(f"      Classification complete.")
        except Exception as e:
            print(f"ERROR during classification: {e}")

        # 4. Build Feature Tree
        try:
            print("[4/4] Reconstructing Feature Tree...")
            if 'FeatDefs' in self.toc:
                offset, _ = self.toc['FeatDefs']
                builder = CreoTreeBuilder(self.target_file)
                builder.load_features(offset)
                builder.build_tree()
                self.tree_adj = builder.adj
                self.all_ids = builder.all_ids
                print(f"      Tree reconstructed.")
            else:
                print("      [SKIP] FeatDefs not in TOC. Cannot build tree.")
                self.all_ids = {f['id'] for f in self.features_data}
        except Exception as e:
            print(f"ERROR building tree: {e}")
            self.all_ids = {f['id'] for f in self.features_data}

        self.report()

    def report(self):
        print(f"\n{'='*60}")
        print(f"FINAL RECONSTRUCTION REPORT")
        print(f"{'='*60}")
        print(f"Total Features found: {len(self.features_data)}")
        
        if self.features_data:
            print(f"\n{'#':<4} | {'ID':<15} | {'TYPE':<15} | {'PARAMS'}")
            print(f"{'-'*65}")
            for i, feat in enumerate(self.features_data[:30], 1):
                type_str = feat['type_info']['type']
                p_str = ", ".join([f"{v[0]}:{v[1]}" for v in feat['params']])
                print(f"{i:<4} | {feat['id']:<15} | {type_str:<15} | {p_str[:40]}...")
            
            if len(self.features_data) > 30:
                print(f"... and {len(self.features_data) - 30} more.")

        if self.tree_adj:
            print(f"\n--- HIERARCHY PREVIEW ---")
            # Print top 10 roots
            all_children = set()
            for children in self.tree_adj.values():
                for c in children:
                    all_children.add(c)
            roots = [i for i in self.all_ids if i not in all_children]
            for root in sorted(roots)[:10]:
                self._print_mini_tree(root, 0)
            if len(roots) > 10: print("...")

        print(f"\n{'='*60}")
        print(f"END OF REPORT")

    def _print_mini_tree(self, node, depth, visited=None):
        if visited is None: visited = set()
        if node in visited: return
        visited.add(node)
        print("  " * depth + f"|- {node}")
        if node in self.tree_adj:
            for child in sorted(self.tree_adj[node]):
                self._print_mini_tree(child, depth + 1, visited)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("USAGE: python creo_orchestrator.py <path_to_prt_file>")
    else:
        orchestrator = CreoOrchestrator(sys.argv[1])
        orchestrator.execute()
