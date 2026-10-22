# 🏁 HANDOVER: Creo PLM Reverse-Engineering Engine

## 🎯 PROJECT GOAL
Build a professional-grade engine to extract part hierarchies (BOM), manufacturing relations, and mirroring patterns from Creo binary files by parsing the internal protocol.

## 📊 CURRENT STATUS
- **Core Decoder**: `creo_protocol_decoder.py` is STABLE (handles `0xe0` signature and endianness).
- **Parser**: `creo_mapping_table_parser.py` is STABLE and synchronized with the mock generator.
- **Mock Generator**: `create_mock.py` is SYNCHRONIZED and supports complex protocol structures.
- **Orchestrator**: `creo_plm_orchestrator.py` is CONCEPTUALLY ready but pending integration with the new parser.

## ✅ RESOLVED: THE "WALL"
The **Synchronization Loop** has been successfully resolved by:
1.  **Protocol Alignment**: Forcing the mock generator to strictly follow the `CreoProtocolDecoder`'s patterns (`0xe0` markers, `0x02` strings, etc.).
2.  **TOC Integration**: Implementing a `#UGC_TOC` header in the mock generator to allow the parser to discover data segments via absolute offsets.
3.  **Pointer Logic**: Fixing the `id_map_info_ptr` logic to use a relative 16-bit LE offset from the start of the `setup_data` block.

## 📚 READING LIST (MUST READ IN ORDER)

1.  **`src\creo_protocol_decoder.py`** — The foundation. Understand how `0xe0` acts as a sync marker.
2.  **`src\creo_mapping_utils.py`** — The logic for converting binary IDs to human-readable structures.
3.  **`creo_mapping_table_parser.py`** — The core extraction logic for mapping tables.
4.  **`creo_plm_orchestrator.py`** — The master loop. See how it branches logic based on "Role" (Part vs Assembly).
5.  **`work\create_mock.py`** — To understand how we simulate the binary environment.
6.  **`PODSkAZKA.MD`** — The "Golden Knowledge". Essential domain context on Creo internal structures.

## 🛠 REQUIRED SKILLS
- **Binary Parsing**: Deep understanding of `struct`, endianness, and signature-based scanning.
- **Regex for Binaries**: Using `re` to find patterns in byte streams.
- **Protocol Synchronization**: Ensuring mock generators and parsers use identical byte-level layouts.

---
**Next Immediate Step**: Integrate the `creo_mapping_table_parser.py` into the `creo_plm_orchestrator.py` to enable automated, managed workflow.
