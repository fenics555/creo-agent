# SKILL: Creo Reverse Engineering (Knowledge Base)

## 1. Core Architecture: Typed Graph
The goal is to build a functional graph where nodes are entities and edges are typed relationships.

## 2. Taxonomy of Relationships (Edges)

### 2.1. Product Geometry (BOM)
* `contains`: Assembly $\rightarrow$ Component.
* `contains_via_instance`: Assembly $\rightarrow$ Component (with instance name).
* `mirror_of`: Part $\rightarrow$ Base Part.
* `derived_from`: Part $\rightarrow$ Parent Model.

### 2.2. Manufacturing Topology (The "How")
**CRITICAL:** Manufacturing data is often external to the geometry. It links a Product to a Process.
* **Hierarchy**: `Product` $\rightarrow$ `Setup (Workcell)` $\rightarrow$ [`Fixture` & `Toolset`].
* **Setup (Workcell)**: A specific technological stage (e.g., `TOK1`, `4X`).
    * *Identity Rule*: If Workcell names match, the Toolset is identical.
* **Fixture**: Found in `CTKD-PSB Приспособления`. Linked to a Setup.
* **Toolset**: A collection of tools (Drill, Mill, Tap, etc.) assigned to a Setup.
    * *Tool Attributes*: Tool ID, Type, Geometry (Chamfer/Extension).

### 2.3. Family Table (Variants)
* `instance_of`: Instance $\rightarrow$ Generic Parent (via `Sld_DrvTable` or `FamilyInf`).

## 3. Critical Pitfalls & Rules

### 3.1. Data Extraction
* **Endianness**: Detect via `MACH SUN_SunOS` or `Windows` headers.
* **Encoding**: Use `latin-1` for binary string extraction; fallback to `cp1251` for parameters.
* **Regex**: Never use Cyrillic in byte-regex literals. Use `rb"\x00([^\x00]{2,48})\x00"`.

### 3.2. Manufacturing Discovery
* **Don't look for "Tool" inside the Part.**
* **Look for "Setup/Workcell Parameters"** (e.g., `&mfg.oper...`) that act as foreign keys to the technological process.

## 4. MdlStatus Specification
* Contains material (`PTC_MATERIAL_NAME`), mass, and audit attributes.
* Key for identifying the "as-built" state of a part.
