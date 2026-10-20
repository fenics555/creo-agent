# Creo Reverse Engineering Toolkit

**Version:** 1.0.0  
**Last Updated:** 20.10.2026

## Description
A professional-grade toolset for surgical extraction of feature trees and parameters from Creo parametric models. This toolkit bypasses the need for a running Creo instance by directly parsing the binary structure of `.prt`, `.asm`, and `.drw` files.

## Architecture

The toolkit is organized into modular components:

### Core Engine
- `src/creo_protocol_decoder.py`: The low-level binary protocol engine. It handles the detection and decoding of `e0` type-indicator headers and ensures robust extraction even in the presence of noise or complex padding.

### Extraction & Analysis
- `src/creo_geom_extractor.py`: The primary scanner. It identifies feature definition markers (`feat_defs_`) and extracts all associated parameters (INT, DOUBLE, STRING).
- `src/creo_tree_builder.py`: The hierarchy reconstructor. It parses parent-child relationships (e.g., `parent_id`, `sub_feat_id`) to build a structured feature tree.
- `src/creo_feature_classifier.py`: The feature type classifier. It uses attribute keys (like `AE_Type`) to identify whether a feature is an Extrude, Sketch, Datum Plane, etc.

### Orchestration
- `creo_orchestrator.py`: The main entry point. It coordinates the full workflow: reading the TOC, scanning features, building the tree, and providing a unified report.

## Usage

To perform a full reverse engineering scan on a Creo file:

```bash
python creo_orchestrator.py <path_to_target_file>
```

Example:
```bash
python creo_orchestrator.py "D:\AI\PROBA\models\...\23-1017gri-02.prt.1"
```

## Directory Structure

- `creo_orchestrator.py`: Main entry point.
- `src/`: Core implementation modules.
- `docs/`: Documentation and technical references.
- `tests/`: Unit and integration tests.
- `work/`: Temporary workspace for processing.
