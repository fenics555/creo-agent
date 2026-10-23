import sys
import os
import re
import struct
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
    Combines pointer-based extraction with semantic LargeText scanning (Gemini-optimized).
    """
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.raw_data = creo_read.read(file_path)
        self.toc = creo_read.parse_toc(self.raw_data)
        self.endian = self._detect_endianness()
        self.decoder = CreoProtocolDecoder(endian=self.endian)
        self.edges: List[CreoEdge] = []
        self.params: Dict[str, Any] = {}
        self.model_name = os.path.basename(file_path).split('.')[0]
        self.large_text_strings: List[str] = []

        # Blacklist of internal Creo TOC/Property names to avoid false BOM components
        self.blacklist = {
            "trf_arr", "plcm_revnum", "next_prop", "merge_info_ptr", "pre_roll_back", 
            "post_roll_back", "post_regen", "parchild_table", "copy_info_ptr", 
            "embed_info_ptr", "copy_info", "embed_info", "trf_arr_ptr", "plcm_revnum_ptr"
        }

    def _detect_endianness(self) -> str:
        return '>' if b"MACH SUN_SunOS" in self.raw_data[:1024] else '<'

    def determine_plm_relation_type(self) -> str:
        """Classifies the entity based on TOC signatures and filename (Gemini logic)."""
        cmnm = self.file_path.lower()
        if "NeuAsmSld" in self.toc or "SolidPersistTable" in self.toc:
            if "FullMData" in self.toc: return "Технологический техпроцесс механообработки (CAM)"
            if "sb" in cmnm or "сб" in cmnm: return "Сборочная единица (Сборка приспособления)"
            return "Конструкторская подсборка"
        if "FeatDefs" in self.toc:
            if cmnm.endswith("_z.prt") or "zag" in cmnm: return "Деталь-заготовка (Предыдущая обработка)"
            if cmnm.endswith("_o.prt") or "otl" in cmnm or "lit" in cmnm: return "Деталь-отливка (Исходный металл)"
            return "Конструкторская деталь (КД)"
        return "Неизвестная сущность PLM"

    def _scan_large_text(self):
        """Extracts all printable strings from the LargeText section for semantic scanning."""
        if "LargeText" in self.toc:
            off, ln = self.toc["LargeText"]
            lt_bytes = self.raw_data[off : off + ln]
            # Try cp1251 first as it's common in RU environments
            matches = re.finditer(rb'[\x20-\xff]{3,64}\x00', lt_bytes)
            for m in matches:
                try:
                    # Try decoding with cp1251, fall back to latin-1
                    s = m.group().decode('cp1251', errors='ignore').strip()
                    if len(s) > 2: self.large_text_strings.append(s)
                except: continue

    def extract_all(self) -> Dict[str, Any]:
        """The main entry point: extracts all types of edges and parameters."""
        print(f"[*] Extracting links for: {self.model_name}")
        print(f"[*] Detected PLM Type: {self.determine_plm_relation_type()}")
        self._scan_large_text()
        self._extract_bom_links()
        self._extract_inheritance_links()
        self._extract_family_links()
        self._extract_audit_links()
        self._extract_mfg_links()
        self._extract_parameters()
        return {
            "model_name": self.model_name,
            "plm_type": self.determine_plm_relation_type(),
            "edges": [e.to_dict() for e in self.edges],
            "parameters": self.params
        }

    def _extract_bom_links(self):
        """BOM links: assembly -> component."""
        for section_name in ["SolidPersistTable", "Comp_Data", "FeatDefsCmp"]:
            if section_name in self.toc:
                off, ln = self.toc[section_name]
                data = self.raw_data[off : off + ln]
                matches = re.finditer(rb'\x00([^\x00]{2,48})\x00', data)
                for m in matches:
                    try:
                        # Try cp1251 then latin-1 to avoid garbled text
                        raw_bytes = m.group(1)
                        try:
                            name = raw_bytes.decode('cp1251').strip()
                        except UnicodeDecodeError:
                            name = raw_bytes.decode('latin-1').strip()
                            
                                                # Sanity check: must be printable and not just random bytes
                        if name and len(name) > 4:
                            printable_chars = sum(1 for c in name if c.isprintable())
                            if printable_chars / len(name) > 0.95:
                                if name.lower() not in self.blacklist and not any(ord(c) < 32 for c in name):
                                    self.edges.append(CreoEdge(self.model_name, name, "bom_component"))
                    except: continue

    def _extract_inheritance_links(self):
        """Inheritance links: mirror/parent relations (Gemini logic)."""
        for s in self.large_text_strings:
            if "BASE_PART" in s.upper() or "GENERIC" in s.upper():
                self.edges.append(CreoEdge(self.model_name, s, "inherit_from_master", {"method": "LargeText_Marker"}))

    def _extract_family_links(self):
        """Family links: part families (Gemini logic)."""
        for s in self.large_text_strings:
            if "ASM_MBR_GENERIC_NAME" in s.upper():
                self.edges.append(CreoEdge(self.model_name, s, "family_instance", {"method": "Generic_Token"}))

    def _extract_audit_links(self):
        """Audit links: history/revision (using creo_read utility)."""
        hist = creo_read.last_hist(self.raw_data)
        if hist and hist[0]: 
            self.edges.append(CreoEdge(self.model_name, "AUDIT_LOG", "has_history", {"rev": hist[0], "author": hist[1], "date": hist[2]}))

    def _extract_mfg_links(self):
        """Extracts manufacturing links using both pointer-based and semantic approaches."""
        print("[*] Starting manufacturing link extraction (Hybrid Mode)...")
        setup_marker = b'setup_data\x00'
        setup_data_pos = self.raw_data.find(setup_marker)
        if setup_data_pos != -1:
            try:
                ptr_marker = b'id_map_info_ptr\x00'
                ptr_marker_pos = self.raw_data.find(ptr_marker, setup_data_pos)
                if ptr_marker_pos != -1:
                    search_pos = ptr_marker_pos + len(ptr_marker)
                    while search_pos + 2 <= len(self.raw_data) and self.raw_data[search_pos] == 0:
                        search_pos += 1
                    ptr_value = struct.unpack('<H', self.raw_data[search_pos : search_pos + 2])[0]
                    entry_pos = setup_data_pos + ptr_value
                    if entry_pos + 4 <= len(self.raw_data):
                        table_offset = struct.unpack('<H', self.raw_data[entry_pos : entry_pos + 2])[0]
                        table_len = struct.unpack('<H', self.raw_data[entry_pos + 2 : entry_pos + 4])[0]
                        table_start = setup_data_pos + table_offset
                        table_end = table_start + table_len
                        if table_start < len(self.raw_data):
                            table_data = self.raw_data[table_start : min(table_end, len(self.raw_data))]
                            setup_id = f"setup_{setup_data_pos:x}"
                            f_fix, f_tool, f_mach, f_op = set(), set(), set(), set()
                            for m in re.finditer(rb'[\x20-\x7E]{3,48}', table_data):
                                try:
                                    s = m.group().decode('ascii').strip()
                                    upper = s.upper()
                                    if re.match(r'^\d+X\d+-\w+$', s): f_fix.add(s)
                                    elif re.match(r'^T\d{3,4}$', s): f_tool.add(s)
                                    elif re.match(r'^(MACH|CNC|MACHINE)\w*$', upper): f_mach.add(s)
                                    elif any(k in upper for k in ['OP', 'STEP', 'TRANSITION', 'FRAZE', 'REZBA', 'SV', 'FR', 'FASKA']): f_op.add(s)
                                except: continue
                            if f_fix: self.edges.append(CreoEdge(self.model_name, "CNC_PROCESS", "mfg_fixture_for", {"fixtures": sorted(f_fix), "setup_id": setup_id}))
                            if f_tool: self.edges.append(CreoEdge(self.model_name, "CNC_PROCESS", "mfg_tool_for", {"tools": sorted(f_tool), "setup_id": setup_id}))
                            if f_mach: self.edges.append(CreoEdge(self.model_name, "CNC_PROCESS", "mfg_machine_for", {"machines": sorted(f_mach), "setup_id": setup_id}))
                            if f_op: self.edges.append(CreoEdge(self.model_name, "CNC_PROCESS", "mfg_operation_of", {"operations": sorted(f_op), "setup_id": setup_id}))
            except Exception as e: print(f"[!] Pointer-based mfg error: {e}")
        f_fix_s, f_tool_s, f_mach_s, f_op_s = set(), set(), set(), set()
        for s in self.large_text_strings:
            u = s.upper()
            if re.match(r'^T\d{3,4}$', s) or any(k in u for k in ['SVERLO', 'FREZA', 'GRAVER']): f_tool_s.add(s)
            elif re.match(r'^(MACH|CNC|MACHINE)\w*$', u): f_mach_s.add(s)
            elif any(k in u for k in ['CHERN', 'CHIST', 'SV', 'FR', 'FASKA', 'RASTOCHKA', 'CENTROVKA', 'DISKOVAYA', 'STEP']): f_op_s.add(s)
            elif re.match(r'^\d+X\d+-\w+$', s): f_fix_s.add(s)
        if f_fix_s: self.edges.append(CreoEdge(self.model_name, "CNC_PROCESS", "mfg_fixture_for", {"fixtures": sorted(f_fix_s), "method": "semantic_large_text"}))
        if f_tool_s: self.edges.append(CreoEdge(self.model_name, "CNC_PROCESS", "mfg_tool_for", {"tools": sorted(f_tool_s), "method": "semantic_large_text"}))
        if f_mach_s: self.edges.append(CreoEdge(self.model_name, "CNC_PROCESS", "mfg_machine_for", {"machines": sorted(f_mach_s), "method": "semantic_large_text"}))
        if f_op_s: self.edges.append(CreoEdge(self.model_name, "CNC_PROCESS", "mfg_operation_of", {"operations": sorted(f_op_s), "method": "semantic_large_text"}))
    def _extract_parameters(self):
        """
        PHASE 2: Parametric Extraction.
        Scans for known numeric parameter signatures in the binary data.
        """
        # Define search markers and their corresponding parameter names
        markers = {
            b'PTC_SHRINKAGE_FACTOR': 'shrinkage_factor',
            b'PTC_MASS': 'mass',
            b'PTC_VOLUME': 'volume',
            b'PTC_DENSITY': 'density'
        }

        for marker, param_name in markers.items():
            idx = self.raw_data.find(marker)
            if idx != -1:
                try:
                    # Look in a 128-byte window after the marker for a double
                    window = self.raw_data[idx : idx + 128]
                    for i in range(0, len(window) - 8, 4):
                        try:
                            val = struct.unpack(self.endian + 'd', window[i:i+8])[0]
                            # Check for reasonable physical ranges to avoid noise
                            if param_name == 'shrinkage_factor' and 0.9 < val < 1.1:
                                self.params[param_name] = round(val, 4)
                                break
                            elif param_name in ['mass', 'volume', 'density'] and 1e-6 < abs(val) < 1e6:
                                self.params[param_name] = round(val, 6)
                                break
                        except: continue
                except Exception as e:
                    print(f"[!] Param extraction error ({param_name}): {e}")

if __name__ == "__main__":
    TEST_FILE = r"D:\AI\tools\agent\creo_reverse_engineering\work\complex_mock.prt"
    if os.path.exists(TEST_FILE):
        extractor = CreoLinksExtractor(TEST_FILE)
        result = extractor.extract_all()
        print(f"[*] Extraction complete for: {result['model_name']}")
        print(f"[*] PLM Type: {result['plm_type']}")
        print(f"[*] Extracted {len(result['edges'])} edges.")
        for e in result['edges']:
            print(f"  {e}")
        print(f"[*] Extracted Parameters: {result['parameters']}")
    else:
        print(f"Test file not found: {TEST_FILE}")





