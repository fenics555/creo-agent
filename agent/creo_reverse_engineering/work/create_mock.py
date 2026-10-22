import struct
import os

def create_mock(file_path, mode="part"):
    """
    Generates different types of mock Creo files.
    Modes:
    - 'part': A simple part with mapping table.
    - 'part_with_parent': A part with mapping table AND inheritance link.
    - 'assembly': An assembly with BOM links (no mapping table).
    """
    
    # 1. Base segments (Mapping Table)
    mt_data = bytearray()
    mt_data.extend(b'\xe0\x03Param_Mass\x00' + struct.pack('<d', 12.345))
    mt_data.extend(b'\xe0\x03Param_Vol\x00' + struct.pack('<d', 0.987))
    mt_data.extend(b'\xe0\x02Fixture_Name\x00' + b'Fixture_10X1-D12\x00')

    # 2. Mode-specific segments
    extra_segments = []
    
    if mode == "part_with_parent":
        # Segment containing the parent model name
        parent_name = b"parent_model.prt\x00"
        extra_segments.append(("Inheritance_Link", b'\xe0\x04' + parent_name))
        
    elif mode == "assembly":
        # Segment containing list of child components
        children = [b"child_1.prt\x00", b"child_2.prt\x00", b"child_3.prt\x00"]
        bom_data = bytearray(b'\xe0\x05' + struct.pack('<I', len(children)))
        for child in children:
            bom_data.extend(child)
        extra_segments.append(("BOM_Links", bom_data))

    # 3. Build Buffer
    buffer = bytearray()
    offsets = {}
    
    # 1. Standard
    standard_segments = [
        ("FeatDefs", b'\xe0\x01body_id\x00\x39\x30\x00\x00'),
        ("SolidPersistTable", b'\xe0\x01bom_id\x00\x01\x00\x00\x00'),
        ("LargeText", b'\xe0\x02CASTING\x00CASTING\x00' + b'\xe0\x02MIRROR_SOURCE\x001001\x00')
    ]
    for name, data in standard_segments:
        offsets[name] = len(buffer)
        buffer.extend(data)
    
    # 2. Extras
    for name, data in extra_segments:
        offsets[name] = len(buffer)
        buffer.extend(data)
        
    # 3. Setup Data (Placeholder)
    setup_start_off = len(buffer)
    setup_name = b"setup_data\x00"
    setup_key = b"id_map_info_ptr\x00"
    # rel_offset is added at the end
    setup_placeholder = setup_name + setup_key + b'\x00\x00' 
    offsets["setup_data"] = setup_start_off
    buffer.extend(setup_placeholder)
    
    # 4. Mapping Table (Only for parts)
    mt_start_off = None
    if mode != "assembly":
        mt_start_off = len(buffer)
        offsets["mapping_table"] = mt_start_off
        buffer.extend(mt_data)
    
    # 5. Fix rel_offset in setup_data
    if mt_start_off is not None:
        rel_offset = mt_start_off - setup_start_off
    else:
        # For assembly, maybe point to some dummy or just 0
        rel_offset = 0
        
    buffer[setup_start_off + len(setup_name) + len(setup_key) : setup_start_off + len(setup_name) + len(setup_key) + 2] = struct.pack('<H', rel_offset)

    # 6. Construct TOC
    toc_lines = []
    for name, off in offsets.items():
        # Size calculation
        sz = 0
        if name == "FeatDefs": sz = len(standard_segments[0][1])
        elif name == "SolidPersistTable": sz = len(standard_segments[1][1])
        elif name == "LargeText": sz = len(standard_segments[2][1])
        elif name == "Inheritance_Link": sz = len(extra_segments[0][1]) if mode == "part_with_parent" else 0
        elif name == "BOM_Links": sz = len(extra_segments[0][1]) if mode == "assembly" else 0
        elif name == "setup_data": sz = len(setup_placeholder)
        elif name == "mapping_table": sz = len(mt_data)
        
        toc_lines.append(f"{name}: {off:08X} {sz:08X}")
    
    toc_header = b"#UGC_TOC\n"
    toc_body = b"\n".join([l.encode('ascii') for l in toc_lines]) + b"\n"
    toc_full = toc_header + toc_body
    
    # 7. Final Write with Absolute Offsets
    toc_len = len(toc_full)
    with open(file_path, 'wb') as f:
        f.write(toc_full)
        absolute_toc_lines = []
        for name, off in offsets.items():
            sz = 0
            if name == "FeatDefs": sz = len(standard_segments[0][1])
            elif name == "SolidPersistTable": sz = len(standard_segments[1][1])
            elif name == "LargeText": sz = len(standard_segments[2][1])
            elif name == "Inheritance_Link": sz = len(extra_segments[0][1]) if mode == "part_with_parent" else 0
            elif name == "BOM_Links": sz = len(extra_segments[0][1]) if mode == "assembly" else 0
            elif name == "setup_data": sz = len(setup_placeholder)
            elif name == "mapping_table": sz = len(mt_data)
            
            absolute_toc_lines.append(f"{name}: {off + toc_len:08X} {sz:08X}")
        
        absolute_toc_full = toc_header + b"\n".join([l.encode('ascii') for l in absolute_toc_lines]) + b"\n"
        f.seek(0)
        f.write(absolute_toc_full)
        f.seek(toc_len)
        f.write(buffer)

    print(f"Created {mode} mock: {file_path}")

if __name__ == "__main__":
    base_dir = r"D:\\AI\\tools\\agent\\creo_reverse_engineering\\work"
    os.makedirs(base_dir, exist_ok=True)
    
    create_mock(os.path.join(base_dir, "simple_mock.prt"), mode="part")
    create_mock(os.path.join(base_dir, "complex_mock.prt"), mode="part_with_parent")
    create_mock(os.path.join(base_dir, "assembly_mock.asm"), mode="assembly")

