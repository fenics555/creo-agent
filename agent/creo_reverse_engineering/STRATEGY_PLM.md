# STRATEGY_PLM: Roadmap for Modernizing plm_reader

## 1. Executive Summary
The current `plm_reader` toolset has successfully established the ability to parse Creo UGC (User Generated Content) containers and generate a functional dependency graph. However, to transition from a "research tool" to an **Enterprise PLM-ready engine**, it must adopt a rigorous, multi-layered, and persistent architecture.

This roadmap, derived from Gemini's "PODSKAZKA" (hints 1-15) engineering analysis, outlines the evolution from a basic parser to a complete **Digital Twin & Life-Cycle Orchestrator**.

---

## 2. Vision: The Enterprise PLM Core
The goal is to move beyond simple "file parsing" and towards **"State & Relationship Management"**.
- **From Files to Entities:** Instead of just reading files, we manage *Entities* (Parts, Assemblies, Processes, Castings).
- **From Static to Dynamic:** Instead of a single snapshot, we manage *Versions* (Snapshots + Delta mutations).
- **From Local to Integrated:** Instead of a local graph, we generate *Standardized Data Packages* (XML/JSON) for ERP (1C:ERP) and PLM (Windchill/Teamcenter) systems.

---

## 3. Technical Foundations (The "Rules of the Game")

To ensure 100% reliability in a heterogeneous environment (Windows/SunOS), the following must be implemented as core system invariants:

### 3.1. Architectural Robustness
- **Dynamic Endianness Detection:** Every parser MUST detect host architecture via the `# - MACH` header. 
  - *Windows/LE:* `<`
  - *SunOS/BE:* `>`
  - **Source:** `PODSkAZKA от ГЕМИНИ11.MD`
- **Precision Binary Access:** Use 16-bit relative offsets (`uint16`) for mapping tables (`id_map_info_ptr`) to avoid Out-of-bounds errors in large files.
  - **Source:** `PODSkAZKA от ГЕМИНИ14.MD`

### 3.2. Data Integrity & Localization
- **Cyrillic-First String Management:** The `LargeText` pool MUST be parsed with a strict `CP1251` decoder, falling back to `latin-1` only when necessary. This is critical for Russian GOST-standards and engineer names.
  - **Source:** `PODSkAZKA от ГЕМИНИ1.MD`, `PODSkAZKA от ГЕМИНИ11.MD`
- **Media Deduplication:** Implement SHA-256 hashing for all embedded graphics (JPEG from `.prt`/`.asm`, BMP from `.drw`) to prevent storage bloat in the PLM database.
  - **Source:** `PODSkAZKA от ГЕМИНИ14.MD`

---

## 4. The 5-Layer Persistent Data Model
The graph must be structured into five distinct, typed layers to reflect the physical manufacturing process:

| Layer | PLM Class | Biological/Physical Analog | Binary Anchor/Signature |
| :--- | :--- | :--- | :--- |
| **Level 1** | **KD Master** | The "Perfect" Design | `FeatDefs` (pure geometry) |
| **Level 2** | **Part-Blank (_Z)** | The "Rough" Machining Part | `MERGE_BASE_PART` (Inheritance) |
| **Level 3** | **Part-Casting (_O)** | The "Molten" Casting | `PTC_SHRINKAGE_FACTOR` (Unshrinkage) |
| **Level 4** | **Master Tooling (MSTR)** | The "Mold" Template | `Parting_Surface` / `Core_Print` |
| **Level 5** | **CAM-Process (ASM_MFG)** | The "Factory" Instructions | `FullMData` (Speeds/Feeds/Toolpath) |

**Linkage Logic:**
- **BOM (Top-Down):** Assembly $\rightarrow$ Components (via `NeuAsmSld`).
- **Genealogy (Bottom-Up):** Component $\rightarrow$ Master (via `MERGE_BASE_PART` in `FeatDefs`).
- **Manufacturing (Process-to-Tool):** CAM $\rightarrow$ Fixture/Machine (via `id_map_info_ptr`).

**Source:** `PODSkAZKA от ГЕМИНИ6 -цепочки связей.MD`, `PODSkAZKA от ГЕМИНИ9.MD`

---

## 5. Implementation Roadmap

### Phase 1: Core Engine Fortification (The "Hardened Parser")
*Objective: Eliminate all "Out of bounds" and "Encoding" errors.*
- [ ] Implement global `EndiannessManager` in `engine.py`.
- [ ] Standardize `CP1251` string extraction across all modules.
- [ ] Refactor `creo_links.py` to use 16-bit relative pointers for all mapping tables.

### Phase 2: The Multi-Layer Graph (The "BOM & Genealogy")
*Objective: Implement the 5-layer logic and bidirectional links.*
- [ ] Upgrade `creo_links.py` to recognize all 5 PLM Classes.
- [ ] Implement the "Bottom-Up" Genealogy parser (detecting `MERGE_BASE_PART`).
- [ ] Implement the "Top-Down" BOM parser (detecting `SolidPersistTable`).

### Phase 3: Versioning & Mutation Tracking (The "Digital Thread")
*Objective: Track "What, When, and How" changes occurred.*
- [ ] Implement **Snapshot-based storage**: Store full feature trees at key intervals.
- [ ] Implement **Delta-based mutation**: Capture only changed dimensions (e.g., `85.0 -> 85.75`) and store them as deltas.
- [ ] Build the `MdlStatus` timeline parser to track user/host/timestamp.

### Phase 4: Enterprise & Visual Layer (The "PLM Dashboard")
*Objective: Make the data actionable and integrable.*
- [ ] **Interactive PDM Dashboard:** Integrate `vis-network.js` for 3D graph navigation and `Chart.js` for mutation history.
- [ ] **ERP/1C Integration:** Develop the `KTS-Exporter` (Technical Specification) and `ECO-Generator` (Engineering Change Order) in XML/JSON.
- [ ] **Automated Reporting:** Generate the `PROD_ECO_MANIFEST` for every major change.

---

## 6. Direct Citations Index (Reference Guide)

- **Endianness/Architecture:** `PODSkAZKA от ГЕМИНИ11.MD` (Sec 2), `PODSkAZKA от ГЕМИНИ14.MD` (Sec 1.1).
- **5-Layer Hierarchy:** `PODSkAZKA от ГЕМИНИ6 -цепочки связей.MD` (Sec 1), `PODSkAZKA от ГЕМИНИ9.MD` (Sec 1).
- **BOM/Genealogy Links:** `PODSkAZKA от ГЕМИНИ7.MD` (Sec 1), `PODSkAZKA от ГЕМИНИ9.MD` (Sec 3).
- **CAM/Manufacturing Data:** `PODSkAZKA от ГЕМИНИ4.MD` (Sec 2), `PODSkAZKA от ГЕМИНИ8.MD` (Sec 1).
- **Mutation/History (Snapshot+Delta):** `PODSkAZKA от ГЕМИНИ11.MD` (Sec 2), `PODSkAZKA от ГЕМИНИ12.MD` (Sec 2).
- **Enterprise Integration (ERP/1C):** `PODSkAZKA от ГЕМИНИ10.MD` (Sec 2), `PODSkAZKA от ГЕМИНИ13.MD` (Sec 3).
- **Media Deduplication:** `PODSkAZKA от ГЕМИНИ14.MD` (Sec 2.1).
