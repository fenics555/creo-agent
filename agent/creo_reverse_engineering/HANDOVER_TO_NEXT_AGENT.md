# HANDOVER TO NEXT AGENT: CREO REVERSE ENGINEERING (LINKS MODULE)

## 🏁 CURRENT STATUS: IN-PROGRESS
The goal is to implement `creo_links.py` to transform Creo binary data into a **Typed Relationship Graph** (not just a tree).

### ✅ DONE
- **Core Architecture**: Defined `CreoEdge` and `CreoLinksExtractor`.
- **BOM Links**: Basic extraction of component/instance data from `FeatDefsCmp`/`Comp_Data`.
- **Inheritance (Mirror)**: Implemented detection for `MERGE_BASE_PART`.
- **Inheritance (Derived)**: Implemented detection for `top_to_part_models`.
- **Family Table**: Implemented detection for instances in `FamilyInf` (Validated with `00080-03.prt`).

### 🚧 IN PROGRESS / BLOCKED
- `_extract_mfg_links`: Currently a stub.
- `_extract_family_links`: Needs to link instances to the actual `GENERIC_PARENT` (via `Sld_DrvTable`).
- `_extract_bom_links`: Needs deeper parsing for complex assembly hierarchies.
- **Validation**: Needs a proper test suite against multiple `.prt` files.

---

## 🧠 IMMEDIATE KNOWLEDGE TRANSFER (STUDY THESE FIRST)

To avoid repeating mistakes and understand the context, **read these files/skills immediately**:

### 1. THE "BRAIN" (Knowledge Base)
- `D:\AI\repo\SKILL_creo_reverse_engineering_knowledge.md` — **READ THIS FIRST**. It contains the confirmed byte patterns and the "Typed Graph" philosophy.

### 2. THE "MAP" (Navigation)
- `D:\AI\repo\SKILL_index.md` — Use this to find relevant skills for manufacturing or advanced parsing.
- `D:\AI\repo\AGENT_index.md` — To understand agent-specific tools.

### 3. THE "IMPLEMENTATION" (Codebase)
- `D:\AI\tools\agent\creo_reverse_engineering\src\creo_links.py` — The main task file.
- `D:\AI\tools\agent\creo_reverse_engineering\src\creo_protocol_decoder.py` — Crucial for understanding how we navigate the binary stream.
- `D:\AI\tools\agent\creo_reverse_engineering\src\creo_read.py` — For understanding TOC and raw data access.

---

## ⚠️ CRITICAL PITFALLS (DON'T REPEAT!)
1. **The Regex Trap**: **NEVER** use non-ASCII characters (like Cyrillic) directly inside a bytes regex (`rb"..."`). This causes `SyntaxError`. 
   * **Solution**: Decode the byte segment to `latin-1` or `utf-8` *before* applying the regex.
2. **The "Write-Once" Rule**: When the file is large, don't try to use `editor` to replace the whole thing. Use PowerShell/`run_commands` to rewrite the file incrementally or via a script to avoid truncation and tool errors.
3. **Assumption Risk**: Do not assume the existence of a component just because it's in the TOC. Always verify the structured data using the `decoder`.

---

## 🚀 NEXT STEPS (ROADMAP)
1. **Deepen BOM**: Map the full assembly-component hierarchy.
2. **Complete Family Table**: Find the `Sld_DrvTable` to link family instances to their generic parents.
3. **Implement Mfg Links**: Extract manufacturing associations (tools, fixtures).
4. **Test Suite**: Create a script that runs the extractor against a suite of known files and validates the graph topology.

**GOOD LUCK. THE GRAPH MUST BE TYPED.**
