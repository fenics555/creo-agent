import os
import json
import glob

# Import the tools
from creo_mapping_table_parser import parse_mapping_table
from src.creo_binary_explorer import CreoBinaryExplorer
from src.creo_protocol_decoder import CreoProtocolDecoder

class CreoPlmOrchestrator:
    def __init__(self, search_path, output_dir):
        self.search_path = search_path
        self.output_dir = output_dir
        self.plm_graph = {
            "assemblies": [],
            "parts_genealogy": [],
            "unknown_entities": []
        }

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def run_cycle(self):
        """Главный цикл обработки всех найденных файлов."""
        print(f"[*] Starting PLM Orchestration Cycle in: {self.search_path}")
        
        # 1. Find all potential files
        files = glob.glob(os.path.join(self.search_path, "**", "*.prt"), recursive=True) + \
                glob.glob(os.path.join(self.search_path, "**", "*.asm"), recursive=True)
        
        print(f"[*] Found {len(files)} candidate files.")

        for file_path in files:
            self._process_file(file_path)

        self._finalize_report()

    def _process_file(self, file_path):
        """Обработка одного файла с учетом его роли."""
        print(f"  > Analyzing: {os.path.basename(file_path)}")
        
        # 2. Call the parser directly (No subprocess!)
        try:
            data = parse_mapping_table(file_path)
        except Exception as e:
            print(f"    [!] Critical error calling parser for {os.path.basename(file_path)}: {e}")
            return

        if data["metadata"]["status"] != "success":
            print(f"    [!] Error parsing {os.path.basename(file_path)}: {data['metadata']['status']}")
            return

        role = data["metadata"].get("detected_role", "Unknown")
        
        # 3. Branching Logic (The Core of the Dependency Graph)
        if "Сборка" in role or "Assembly" in role:
            self._handle_assembly_downwards(file_path, data)
        elif "Деталь" in role or "Part" in role:
            self._handle_part_upwards(file_path, data)
        else:
            print(f"    [?] Unknown role: {role}. Skipping complex logic.")
            self.plm_graph["unknown_entities"].append({
                "file": file_path, 
                "role": role,
                "mapping_count": len(data["mapping_table"])
            })

    def _handle_assembly_downwards(self, file_path, data):
        """Логика для графа 'СВЕРХУ-ВНИЗ' (BOM)."""
        print(f"    [+] Role: {data['metadata']['detected_role']} -> Building BOM (Downwards)")
        
        children = []
        try:
            explorer = CreoBinaryExplorer(file_path)
            decoder = CreoProtocolDecoder(endian='<')
            
            # Extract children from BOM_Links segment
            bom_entries = explorer.get_decoded_values("BOM_Links", decoder)
            for entry in bom_entries:
                # In our mock, children are just strings
                children.append(entry["value"])
                
        except Exception as e:
            print(f"    [!] Error extracting BOM: {e}")

        self.plm_graph["assemblies"].append({
            "master_file": file_path,
            "role": data["metadata"]["detected_role"],
            "components": children
        })

    def _handle_part_upwards(self, file_path, data):
        """Логика для графа 'СНИЗУ-ВВЕРХ' (Inheritance)."""
        print(f"    [+] Role: {data['metadata']['detected_role']} -> Tracing Genealogy (Upwards)")
        
        parent_link = None
        try:
            explorer = CreoBinaryExplorer(file_path)
            decoder = CreoProtocolDecoder(endian='<')
            
            # Extract parent from Inheritance_Link segment
            inheritance_entries = explorer.get_decoded_values("Inheritance_Link", decoder)
            if inheritance_entries:
                # Assume the first entry is the parent name
                parent_link = inheritance_entries[0]["value"]
                
        except Exception as e:
            print(f"    [!] Error extracting Genealogy: {e}")

        self.plm_graph["parts_genealogy"].append({
            "part_file": file_path,
            "role": data["metadata"]["detected_role"],
            "parent_link": parent_link
        })

    def _finalize_report(self):
        """Сборка финальной ПЛМ-матрицы."""
        report_path = os.path.join(self.output_dir, "FINAL_PLM_GRAPH_REPORT.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.plm_graph, f, indent=4, ensure_ascii=False)
        print(f"\n[!] Orchestration Cycle Complete.")
        print(f"[!] Final PLM Graph Report: {report_path}")

if __name__ == "__main__":
    # Configuration for testing
    SEARCH_DIR = r"D:\AI\tools\agent\creo_reverse_engineering\work"
    OUTPUT = r"D:\AI\log\creo_reverse_engineering\orchestration_results"

    orchestrator = CreoPlmOrchestrator(SEARCH_DIR, OUTPUT)
    orchestrator.run_cycle()
