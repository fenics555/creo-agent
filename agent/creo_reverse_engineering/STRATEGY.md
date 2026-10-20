# 🏗️ CREO REVERSE ENGINEERING: MASTER STRATEGY

## 📌 PART 1: ERROR LOG & SOLUTIONS (Lessons Learned)

| # | Module | Problem | Solution |
|---|---|---|---|
| 1 | extractor vs tree_builder | `scan_all_features` reads `AllFeatur`, `load_features` — `FeatDefs`. ID mismatch | Both must use `AllFeatur`; `FeatDefs` is ONLY for schema reference |
| 2 | tree_builder | `feat_defs_917/940/1000` are schema versions, NOT feature IDs | Use `id`/`feat_id` inside record or `IdsGenInfoDb → feat_list_ids` |
| 3 | **DECODER (CRITICAL)** | `val_end = data.find(b'\xe0')` truncates values if `0xe0` is inside INT/DOUBLE | **STOP USING find(b'\xe0')**. Read exact N bytes based on type |
| 4 | **DECODER (CRITICAL)** | `DOUBLE` read as `>d` (big-endian) in Windows files | Detect endianness via `MACH` header (Windows=LE, SunOS=BE) |
| 5 | extractor | `record = feat_data[curr:next_off]` only captures one field | Accumulate `record` until next `feat_id` or boundary |
| 6 | classifier | Searching for `AE_Type`, `type`, `ft_type` fails | Use `feattype_key`, `feat_type_ptr`, or `symbol_key` |
| 7 | classifier | `TYPE_MAP` is guesswork | Calibrate using known PDF/Models (Extrude, Hole, Round) |
| 8 | decoder | Non-e0 mode captures random bytes as names/values | Disable non-e0 mode for `AllFeatur`/`FeatDefs` |
| 9 | model_parser | `_process_dependency_block` generates `[0,1,…,size-1]` (fake geom) | Parse real `comp_id`, `asm_map_sys`, `geom_own_tbl` from `GeomDepen` |
| 10 | orchestrator | `feat['id']` can be `None` | Always use `fid = feat.get('id') or 'N/A'` |
| 11 | tree_builder | `sorted(roots)` fails on mixed types | Use `sorted(roots, key=str)` |
| 12 | test scripts | Hardcoded offsets (15527, 27069) | Always use `parse_toc(data)` |
| 13 | extractor | `scan_all_features` re-parses file unnecessarily | Pass `data` and `toc` objects directly |

---

## 🔍 PART 2: DOMAIN KNOWLEDGE (The Clues)

### 2.1. File Anatomy & TOC
* **Header**: Contains `#UGC:2`, `MACH` (Endianness!), `UOBJ_ID`, and `CMNM` (filename).
* **TOC Structure**: `name hex_offset hex_size hex_unpacked hex_magic hex_flag hex_ref crc1 crc2`.
* **TOC Flags**: `flag=9` (Normal), `flag=a` (Sub-section), `flag=c` (Table).
* **Nesting**: `ND:0:Model_L05_PX` indicates nested nodes.

### 2.2. Section Detection (Magic Bytes)
* `\x1f\x8b` $\to$ **GZIP** (Always decompress before parsing!).
* `\xff\xd8\xff` $\to$ **JPEG** (Preview).
* `Sld_` $\to$ **Structured Binary**.
* `#UGC` $\to$ **ASCII Text**.

### 2.3. The "e0" Protocol Reality
* `e0` is a **Block Separator**, not a field delimiter.
* Inside a block: `[type_byte][name]\0[value_data]`.
* **Rule**: Read exact N bytes for `type_byte` (0x01=4, 0x03=8, etc.). **NEVER** search for the next `e0` to find the end of a value.

### 2.4. Relationship Anchors
* **Inheritance/Deriving**: `MdlRefInfo.top_to_part_models` and `FeatRefData`.
* **BOM**: `Dwg_Models` (in ASM) or `FeatDefsCmp` (in PRT).
* **Family Table**: `FamilyInf.drv_tbl_ptr` $\to$ `Sld_DrvTable`.
* **External Ref**: `p_foreign_source` or `ext`.
* **Manufacturing**: `Mfg_info → tool_array`.
* **Revision/Rename**: `MdlStatus → mtrack_data`.

---

## 🔗 PART 3: CONNECTION THEORY (Deep Links)

### 3.1. Four Types of Connections to Detect

1.  **Inheritance / Deriving (inherit):**
    * `06700423-01.prt` $\leftarrow$ `226_595-223_985-136_3-01` (via `MdlRefInfo.top_to_part_models` or `FeatRefData`).
    * `06700423-01_z.prt` (stock) $\leftarrow$ same source.
2.  **BOM (Inclusion):**
    * `06700423-01.asm` contains `06700423-01.PRT` (via `Dwg_Models`).
3.  **Family Table (Instances):**
    * `bolt.prt` (generic) $\to$ `bolt_m6x20.prt` (instance) $\to$ `assembly_A.asm` (used in).
4.  **External References (xref):**
    * `p_foreign_source` or `ext` links.

### 3.2. Family Table Logic (The "Instance" Problem)
A generic part (e.g., `bolt.prt`) isn't directly in a BOM. The **instance** is.
* **The Link**: `Generic` $\to$ `FamilyInf` $\to$ `Sld_DrvTable` $\to$ `instances`.
* **Transitive Closure**: `Assembly` $\to$ `Instance` $\to` `Generic`.
* **Reporting**: Show "Direct" (if generic is used) and "Indirect" (if instance is used) connections.

---



## 🛠️ PART 4: IMPLEMENTATION & UI (Tactical)

### 4.1. Implementation Roadmap

#### 🔴 Priority 1: Core Engine Fixes
* **Decoder**: Implement strict length reading (no `find(e0)`). Implement endianness detection via `MACH`.
* **Extractor**: Capture the entire `record` block (from one `feat_id` to the next) for the classifier.
* **Mapping**: Build `body_id` $\to$ `feat_id` map in `AllFeatur` to link `GeomDepen`.

#### 🟠 Priority 2: Connection Logic
* **Family Parser**: Module to parse `FamilyInf` and `Sld_DrvTable`.
* **Component Parser**: Module to extract `instance_name` from `FeatDefsCmp`.
* **Graph Resolver**: A module that builds a graph with edge types (`inherit`, `component`, `instance_of`, `used_in`).

#### 🟡 Priority 3: UI & Reporting
* **Visualizer**: Show connections as `Direct` vs `Via Instance`.
* **Smart Warnings**: "Renaming this part will affect N instances in M assemblies."

### 4.2. Recommended Modules for CR-Toolkit

1.  **`creo_family_parser.py`**: For `FamilyInf` and `Sld_DrvTable`.
2.  **`creo_component_parser.py`**: For `FeatDefsCmp` (instance names/parent/ext).
3.  **`creo_connection_graph.py`**: To handle the transitive closure (Assembly $\to$ Instance $\to$ Generic).
4.  **`creo_connection_resolver.py`**: The orchestrator that reports "Who uses what".

### 4.3. Implementation Recipes

* **Detect Section Type**: Use magic bytes (`\x1f\x8b` for gzip, `\xff\xd8` for jpeg, `Sld_` for structured, `#UGC` for ASCII).
* **Find All Links**: Use `MdlRefInfo` for upstream, `Dwg_Models` for BOM, and `FeatDefsCmp` for instances.
* **Handle Names**: Always check for `instance_name` vs `name`.

---
*(End of Strategy)*
