# 🏁 RELAY: Reverse Engineering Creo Manufacturing Setup Data

## 🎯 GOAL
Extract the unique manufacturing setup identifier (the "Golden Key") from the `setup_data` binary block to perform a global search for the associated fixture (part/assembly) across the PLM directory (`Z:\PTC\Work\...`).

## 🧠 CURRENT KNOWLEDGE (The "Discovery")
The `setup_data` block is not a flat list; it is a **linked list of parameter blocks**. The navigation follows a specific chain of pointers/descriptors:

**The Navigation Chain:**
`setup_type` $\rightarrow$ `setup_id` $\rightarrow$ `attr` $\rightarrow$ `appl_id` $\rightarrow$ `setup_data`

**Critical Parameters Identified:**
- `appl_id`: Identifies the context (e.g., `05` for Manufacturing).
- `id_map_info_ptr`: **THE NAVIGATOR**. This is a pointer (integer/offset) that leads to a mapping table linking the setup to a specific Tool/Fixture ID.
- `setup_data(da_setup_point/icon)`: The sub-blocks containing the actual payload.

**Current Status:**
- Numerical search for direct IDs (e.g., `151061240`) in the whole directory yielded no results.
- **Hypothesis**: The "Golden Key" is either a **String** (part of a naming convention) or a **pointer-based mapping** that requires following the `id_map_info_ptr`.

## 🛠️ TOOLBOX (Python Scripts)
These tools are located in: `D:\AI\tools\agent\creo_reverse_engineering\work\`

1.  `value_dumper_v2.py`: Deep binary inspection. Dumps Name-String-Integer triplets around a key.
2.  `creo_graph_navigator.py`: Scans all `setup_data` nodes in a file and lists all candidate strings and integers.
3.  `extract_all_strings.py`: Targeted extraction of all printable sequences from a specific block.
4.  `search_fixture_by_id.py`: Attempts to find files by searching for specific 4-byte integer IDs.

## 📚 REQUIRED SKILLS (Read these first!)
To understand the logic, you **MUST** read these files in `D:\AI\repo\Creo\`:
- `SKILL_mfg_parameter_blocks.md`: Defines the structure of the parameter blocks.
- `SKILL_parameter_graph_navigation.md`: Explains the "Chain of Command" and how to follow pointers.
- `SKILL_GRABLI.md`: Lists common pitfalls (regex, encoding, binary offsets).

## 📂 REQUIRED FILES
- **Target File**: `Z:\PTC\Work\001_15 ЦТКД Электон\ЦТКД 738.01.001-01 Фланец\ctkd_738_01_001-01.prt.11`
- **Scripts**: All scripts listed in the Toolbox above.

## ⏭️ NEXT STEPS (Immediate Action)
1.  **Run `extract_all_strings.py`** on the target file to find any strings that look like part numbers or fixture names (e.g., `CTKD-...`, `738-...`).
2.  **Analyze the `id_map_info_ptr`**: Use the value found to see if it points to a recognizable structure in the file.
3.  **Search for Strings**: Once a candidate string is found, use `Get-ChildItem -Recurse` or a Python script to search for that string in the entire `Z:\PTC\Work\...` tree.
