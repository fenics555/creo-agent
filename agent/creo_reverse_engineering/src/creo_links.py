import sys
import os
import re
from typing import List, Dict, Any, Tuple, Set

# Add paths to sys.path
sys.path.append(r'D:\AI\tools\agent')
sys.path.append(r'D:\AI\tools\agent\creo_reverse_engineering\src')

from plm_reader import creo_read
from creo_protocol_decoder import CreoProtocolDecoder

class CreoEdge:
    """Represents a relationship in the Creo graph."""
    def __init__(self, source: str, target: str, edge_type: str, metadata: Dict[str, Any] = None):
        self.source = source
        self.target = target
        self.type = edge_type
        self.metadata = metadata or {}

    def __repr__(self):
        meta_str = ""
        if self.metadata:
            meta_str = " | " + str(self.metadata)
        return f"({self.source}) --[{self.type}]--> ({self.target}){meta_str}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "type": self.type,
            "metadata": self.metadata
        }

class CreoLinksExtractor:
    """
    Extracts typed relationships (edges) from Creo files to build a functional graph.
    Implementation Deepened with Gemini PODSkAZKA knowledge.
    """
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.raw_data = creo_read.read(file_path)
        self.toc = creo_read.parse_toc(self.raw_data)
        self.endian = self._detect_endianness()
        self.decoder = CreoProtocolDecoder(endian=self.endian)
        self.edges: List[CreoEdge] = []
        self.model_name = os.path.basename(file_path).split('.')[0]

    def _detect_endianness(self) -> str:
        return '>' if b"MACH SUN_SunOS" in self.raw_data[:1024] else '<'

    def determine_plm_relation_type(self) -> str:
        """Classifies the entity based on TOC signatures and filename."""
        if "NeuAsmSld" in self.toc or "SolidPersistTable" in self.toc:
            if "FullMData" in self.toc:
                return "Технологический техпроцесс механообработки (CAM)"
            return "Сборочная единица (Сборка)"
        
        if "FeatDefs" in self.toc:
            cmnm = self.file_path.lower()
            if "_z" in cmnm or "_zag" in cmnm:
                return "Деталь-заготовка (Предыдущая обработка)"
            if "_o" in cmnm or "_otl" in cmnm:
                return "Деталь-отливка (Исходный металл)"
            return "Конструкторская деталь (КД)"
            
        return "Неизвестная сущность PLM"

    def extract_all(self) -> List[Dict[str, Any]]:
        """The main entry point: extracts all types of edges."""
        print(f"[*] Extracting links for: {self.model_name}")
        print(f"[*] Detected PLM Type: {self.determine_plm_relation_type()}")
        
        self._extract_bom_links()
        self._extract_inheritance_links()
        self._extract_family_links()
        self._extract_audit_links()
        self._extract_mfg_links()
        
        return [e.to_dict() for e in self.edges]

    def _extract_bom_links(self):
        """BOM links: assembly -> component."""
        for section_name in ["SolidPersistTable", "Comp_Data", "FeatDefsCmp"]:
            if section_name in self.toc:
                off, ln = self.toc[section_name]
                data = self.raw_data[off : off + ln]
                matches = re.finditer(rb'\x00([^\x00]{2,48})\x00', data)
                found_names = []
                for m in matches:
                    try:
                        name = m.group(1).decode('latin-1').strip()
                        if name and name != self.model_name:
                            found_names.append(name)
                    except: continue
                for name in found_names:
                    self.edges.append(CreoEdge(
                        source=self.model_name,
                        target=name,
                        edge_type="contains_via_instance",
                        metadata={"section": section_name}
                    ))

    def _extract_inheritance_links(self):
        """Inheritance: Part -> Parent (via top_to_part_models or MERGE_BASE_PART)."""
        patterns = {
            "top_to_part_models": rb'top_to_part_models\x00([^\x00]+)\x00',
            "MERGE_BASE_PART": rb'MERGE_BASE_PART\x00([^\x00]+)\x00'
        }
        for rel_type, pattern in patterns.items():
            matches = re.finditer(pattern, self.raw_data)
            for m in matches:
                try:
                    parent_name = m.group(1).decode('latin-1').strip()
                    self.edges.append(CreoEdge(
                        source=self.model_name,
                        target=parent_name,
                        edge_type="inherit" if "top" in rel_type else "mirror_of",
                        metadata={"method": rel_type}
                    ))
                except: continue

    def _extract_family_links(self):
        """Family Table: Instance -> Generic Parent."""
        if "FamilyInf" in self.toc:
            off, ln = self.toc["FamilyInf"]
            data = self.raw_data[off : off + ln]
            matches = re.finditer(rb'\x00([^\x00]{2,48})\x00', data)
            names = []
            for m in matches:
                try:
                    name = m.group(1).decode('latin-1').strip()
                    if name: names.append(name)
                except: continue
            for i in range(0, len(names) - 1, 2):
                self.edges.append(CreoEdge(
                    source=names[i],
                    target=names[i+1],
                    edge_type="instance_of",
                    metadata={"family_table": True}
                ))
    def _extract_audit_links(self):
        """Audit: Extracts attributes from MdlStatus."""
        if "MdlStatus" not in self.toc:
            return
        off, ln = self.toc["MdlStatus"]
        section_data = self.raw_data[off : off + ln]
        
        patterns = {
            "user": rb'user_name\x00([^\x00]+)\x00',
            "version": rb'Proe_version\x00([^\x00]+)\x00'
        }
        # For Cyrillic, we use encoded bytes
        comp_pattern = "Наименование компьютера:\\s*'([^']+)'".encode('cp1251')
        
        metadata = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, section_data)
            if match:
                try:
                    val = match.group(1).decode('latin-1')
                    metadata[key] = val.strip()
                except: continue
        
        comp_match = re.search(comp_pattern, section_data)
        if comp_match:
            try:
                metadata["computer"] = comp_match.group(1).decode('cp1251').strip()
            except: pass

        if metadata:
            self.edges.append(CreoEdge(
                source=self.model_name,
                target="AUDIT_LOG",
                edge_type="has_history",
                metadata=metadata
            ))

    def _extract_mfg_links(self):
        """Manufacturing: stock, tool, fixture from FullMData/LargeText."""
        if "LargeText" in self.toc:
            off, ln = self.toc["LargeText"]
            lt_data = self.raw_data[off : off + ln]
            cam_keywords = [b'CHERN', b'CHIST', b'SV', b'FR', b'FASKA', b'RASTOCHKA', b'CENTROVKA']
            found_ops = set()
            for kw in cam_keywords:
                if kw in lt_data:
                    match = re.search(rb'[^\x00]*' + kw + b'[^\x00]*', lt_data)
                    if match:
                        try:
                            op_name = match.group().decode('cp1251', errors='ignore').strip()
                            found_ops.add(op_name)
                        except: continue
            if found_ops:
                tool_matches = re.finditer(rb'T\d{4}', lt_data)
                tools = []
                for tm in tool_matches:
                    try: tools.append(tm.group().decode('ascii'))
                    except: continue
                self.edges.append(CreoEdge(
                    source=self.model_name,
                    target="CNC_PROCESS",
                    edge_type="machining_route",
                    metadata={
                        "operations": sorted(list(found_ops)),
                        "tools": sorted(list(set(tools)))
                    }
                ))

if __name__ == "__main__":
    TEST_FILE = r"D:\AI\tools\agent\creo_reverse_engineering\work\complex_mock.prt"
    if os.path.exists(TEST_FILE):
        extractor = CreoLinksExtractor(TEST_FILE)
        edges = extractor.extract_all()
        print(f"Extracted {len(edges)} edges:")
        for e in edges:
            print(f"  {e}")
    else:
        print(f"Test file not found: {TEST_FILE}")
