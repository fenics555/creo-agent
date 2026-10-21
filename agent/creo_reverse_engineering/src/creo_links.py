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
        meta_str = f" | {self.metadata}" if self.metadata else ""
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
    """
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.raw_data = creo_read.read(file_path)
        self.toc = creo_read.parse_toc(self.raw_data)
        self.endian = self._detect_endianness()
        self.decoder = CreoProtocolDecoder(endian=self.endian)
        self.edges: List[CreoEdge] = []

    def _detect_endianness(self) -> str:
        return '>' if b"MACH SUN_SunOS" in self.raw_data[:1024] else '<'

    def extract_all(self) -> List[Dict[str, Any]]:
        """The main entry point: extracts all types of edges."""
        print(f"DEBUG: TOC contains: {list(self.toc.keys())}")
        self._extract_bom_links()
        self._extract_inheritance_links()
        self._extract_family_links()
        self._extract_audit_links()

        self._extract_mfg_links()
        if "MdlStatus" in self.toc:
            print("DEBUG: --- MdlStatus Section Start ---")
            off, ln = self.toc["MdlStatus"]
            section_data = self.raw_data[off : off + ln]
            print(f"DEBUG: MdlStatus length: {ln}")
            print(f"DEBUG: MdlStatus header: {section_data[:100]!r}")
            print("DEBUG: --- MdlStatus Section End ---")
        return [e.to_dict() for e in self.edges]

    def _extract_bom_links(self):
        """
        BOM links: assembly -> component.
        Looking for component data in assemblies.
        """
        for section_name, (offset, length) in self.toc.items():
            if "FeatDefsCmp" in section_name or "Comp_Data" in section_name:
                section_data = self.raw_data[offset : offset + length]
                self._parse_component_section(section_name, section_data, offset)

    def _parse_component_section(self, section_name: str, data: bytes, base_offset: int):
        """Parses component data to find target component names and instance names."""
        curr = 0
        assembly_name = self._get_current_model_name()
        while curr < len(data):
            val, next_off, v_type, name = self.decoder.decode_next_value(data, curr)
            if not name or v_type == "EOF":
                break
            
            if v_type == "STRING" and len(name) > 2:
                # In component sections, we often have [ComponentName] [InstanceName]
                next_val, next_next_off, next_v_type, next_name = self.decoder.decode_next_value(data, next_off)
                
                if next_v_type == "STRING" and next_name:
                    self.edges.append(CreoEdge(
                        source=assembly_name,
                        target=name,
                        edge_type="contains_via_instance",
                        metadata={"instance_name": next_name, "comp_name": name}
                    ))
                else:
                    self.edges.append(CreoEdge(
                        source=assembly_name,
                        target=name,
                        edge_type="contains",
                        metadata={"comp_name": name}
                    ))
                
                curr = next_next_off if next_next_off > curr else next_off + 1
            else:
                curr = next_off if next_off > curr else curr + 1

    def _extract_inheritance_links(self):
        """
        Inheritance: part -> parent (derive), part -> base (mirror/stock).
        """
        # 1. Mirror/Stock: Looking for MERGE_BASE_PART
        if b"MERGE_BASE_PART" in self.raw_data:
            matches = re.finditer(rb"MERGE_BASE_PART\x00([A-Za-z0-9_\-\.]{4,47})\x00", self.raw_data)
            for m in matches:
                base_name = m.group(1).decode('latin-1')
                self.edges.append(CreoEdge(
                    source=self._get_current_model_name(),
                    target=base_name,
                    edge_type="mirror_of",
                    metadata={"role": "stock/mirror"}
                ))

        # 2. Derived/Inherit: Looking for MdlRefInfo or FeatRefData
        if b"MdlRefInfo" in self.raw_data or b"top_to_part_models" in self.raw_data:
            matches = re.finditer(rb"top_to_part_models\x00([A-Za-z0-9_\-\.]{4,47})\x00", self.raw_data)
            for m in matches:
                parent_name = m.group(1).decode('latin-1')
                self.edges.append(CreoEdge(
                    source=self._get_current_model_name(),
                    target=parent_name,
                    edge_type="inherit",
                    metadata={"relation": "derived"}
                ))

    def _extract_family_links(self):
        """
        Family Table: instance -> generic.
        """
        if b"FamilyInf" not in self.raw_data:
            return

        drv_tbl_offset = None
        instances = []

        # 1. Parse FamilyInf to find instances and the pointer to the table
        for section_name, (offset, length) in self.toc.items():
            print(f"DEBUG: Checking section: {section_name}")
            if "FamilyInf" in section_name:
                print(f"DEBUG: Found FamilyInf section: {section_name} at {offset}")
                section_data = self.raw_data[offset : offset + length]
                curr = 0
                while curr < len(section_data):
                    val, next_off, v_type, name = self.decoder.decode_next_value(section_data, curr)
                    if not name or v_type == "EOF":
                        break
                    
                    print(f"DEBUG: Decoded value: {val} (type: {v_type}, name: {name})")
                    
                    if name == "drv_tbl_ptr":
                        if isinstance(val, int):
                            drv_tbl_offset = val
                        elif isinstance(val, str) and val.isdigit():
                            drv_tbl_offset = int(val)
                    elif name in ("FamilyInfo", "inherit_rep", "generics", "instances"):
                        pass
                    else:
                        if isinstance(val, str) and len(val) > 2 and val.isprintable():
                            instances.append(val)
                    
                    curr = next_off
                break

        # 2. Attempt to resolve the generic parent
        target_data = None
        if drv_tbl_offset and drv_tbl_offset > 0:
            target_data = self.raw_data[drv_tbl_offset:]
        elif "Sld_DrvTable" in self.toc:
            off, ln = self.toc["Sld_DrvTable"]
            target_data = self.raw_data[off : off + ln]
        elif "DrvTable" in self.toc:
            off, ln = self.toc["DrvTable"]
            target_data = self.raw_data[off : off + ln]

        if target_data:
            # The table is a sequence of null-terminated strings (pairs: inst, gen)
            matches = re.finditer(rb"\x00([^\x00]{2,48})\x00", target_data)
            names_in_table = []
            for m in matches:
                try:
                    names_in_table.append(m.group(1).decode('latin-1'))
                except:
                    continue
            
            for i in range(0, len(names_in_table) - 1, 2):
                inst = names_in_table[i]
                gen = names_in_table[i+1]
                if inst and gen:
                    self.edges.append(CreoEdge(
                        source=inst,
                        target=gen,
                        edge_type="instance_of",
                        metadata={"family_table": True}
                    ))
        else:
            for inst in instances:
                if inst:
                    self.edges.append(CreoEdge(
                        source=inst,
                        target="GENERIC_PARENT",
                        edge_type="instance_of",
                        metadata={"family_table": True}
                    ))



    def _extract_mfg_links(self):
        """
        Manufacturing: stock, tool, fixture.
        """
        if b"Mfg_info" in self.raw_data:
            # Parsing Mfg_info is heavy; for now, look for common markers
            pass

    def _extract_audit_links(self):
        """
        Audit: Extracts attributes from MdlStatus.
        """
        if "MdlStatus" not in self.toc:
            return

        off, ln = self.toc["MdlStatus"]
        section_data = self.raw_data[off : off + ln]
        
        # Basic scanner for [Attribute] = [Value] patterns in the MdlStatus section
        # Since we don't know the exact structure, we look for null-delimited strings
        matches = re.finditer(rb"\x00([^\x00]{2,48})\x00", section_data)
        attributes = []
        for m in matches:
            try:
                attr = m.group(1).decode('latin-1')
                if attr.strip():
                    attributes.append(attr)
            except:
                continue
        
        # If we found attributes, we can add them as metadata to the model itself
        # For now, we'll just print them to verify
        if attributes:
            # In a real implementation, these would be part of the model's property graph
            pass

    def _extract_mfg_links(self):
        """
        Manufacturing: stock, tool, fixture.
        """
        if b"Mfg_info" in self.raw_data:
            # Parsing Mfg_info is heavy; for now, look for common markers
            pass

    def _get_current_model_name(self) -> str:
        """Returns the name of the file being processed."""
        return os.path.basename(self.file_path).split('.')[0]

if __name__ == "__main__":
    # Test script
    TEST_FILE = r"D:\AI\PROBA\models\00080-03.prt"
    if os.path.exists(TEST_FILE):
        extractor = CreoLinksExtractor(TEST_FILE)
        edges = extractor.extract_all()
        print(f"Extracted {len(edges)} edges:")
        for e in edges:
            print(f"  {e}")
    else:
        print(f"Test file not found: {TEST_FILE}")
