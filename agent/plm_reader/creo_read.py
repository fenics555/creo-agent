# -*- coding: utf-8 -*-
"""creo_read вЂ” PART 1"""

import datetime
import os
import re
import struct
from collections import Counter

try:
    import creo_tree_reader
except ImportError:
    creo_tree_reader = None

TAIL = re.compile(rb"\xf7(.)\xe3([0-9]{1,7})\x00\x00(.{0,220}?)\x00((?:Creo )?[0-9][0-9.]*)\x00", re.S)
STAMP = re.compile(rb"\xf7\x14([\x20-\x7e\xc0-\xff]{1,24}?)\x00\xe2(.)(.)(.)(.)(.)(.)", re.S)
STAMP2 = re.compile(rb"\xe1\xf6\xe1([\x20-\x7e\xc0-\xff]{1,24}?)\x00\xe2(.)(.)(.)(.)(.)(.)", re.S)
NAME_B = re.compile(rb"[\x00-\x1f\x80-\xff]([A-Za-z0-9][A-Za-z0-9_\-\.]{3,47}\.(?:PRT|ASM))", re.IGNORECASE)

def stem(name):
    n = name.upper()
    for ext in (".PRT", ".ASM", ".DRW", ".NEU", ".SEC", ".M_P", ".PRT.", ".ASM."):
        if ext in n: n = n.split(ext)[0]; break
    return re.sub(r"\.\d+$", "", n)

def read(path):
    with open(path, "rb") as f: return f.read()

def parse_toc(raw):
    out, pos = {}, raw.find(b"#UGC_TOC")
    for _ in range(20):
        if pos < 0: break
        p = raw.find(b"\n", pos)
        nxt = -1
        while True:
            e = raw.find(b"\n", p + 1)
            if e < 0: break
            line = raw[p + 1:e].decode("ascii", "replace").strip()
            p = e
            if line.startswith("NEXT_TOC_ENTRY"):
                nxt = int(line.split()[1], 16); break
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_:]{1,40}) ([0-9a-f]{2,8}) ([0-9a-f]{2,8})(?: ([0-9a-f]{2,8}))?(.*)$", line)
            if m and (not m.group(5).strip() or m.group(5).strip()[0] in "0123456789-"):
                ln = int(m.group(4), 16) if m.group(4) else int(m.group(3), 16)
                key = m.group(1)
                nd_re = re.compile(r"^ND:\d+:(.+?)(?::\d+)?$")
                nd_match = nd_re.match(key)
                if nd_match: key = nd_match.group(1)
                out[key] = (int(m.group(2), 16), max(ln, 1))
        if nxt < 0 or nxt >= len(raw): break
        pos = nxt
    return out

def _endian(raw):
    return "big" if b"MACH SUN_SunOS" in raw[:512] else "little"

def parse_record_flow(data, start_pos):
    results = {}
    dict_start = data.find(b'\xe1\xe0', start_pos)
    if dict_start == -1: return results, "No dictionary (e1e0) found."
    boundary_pos = data.find(b'\xe1\xf1', dict_start)
    if boundary_pos == -1: return results, "No boundary (e1f1) found after dictionary."
    field_names = []
    curr = dict_start + 2 
    while curr < boundary_pos:
        null_pos = data.find(b'\x00', curr)
        if null_pos == -1 or null_pos >= boundary_pos: break
        name = data[curr:null_pos].decode('ascii', errors='replace').strip('\x00')
        if name: field_names.append(name)
        curr = null_pos + 1
    end_pos = data.find(b'\xe1\xe1', boundary_pos)
    if end_pos == -1: end_pos = len(data)
    curr = boundary_pos + 2 
    while curr < end_pos:
        f7_pos = data.find(b'\xf7', curr, end_pos)
        if f7_pos == -1: break
        idx = data[f7_pos + 1]
        e3_pos = data.find(b'\xe3', f7_pos + 2, end_pos)
        if e3_pos == -1: break
        val_start = e3_pos + 1
        if val_start >= end_pos: break
        type_code = data[val_start]
        if type_code == 0xe0:
            if val_start + 9 <= end_pos:
                val = struct.unpack('>d', data[val_start+1:val_start+9])[0]
                val_end = val_start + 9
            else: break
        elif type_code == 0xe2:
            if val_start + 5 <= end_pos:
                val = struct.unpack('>i', data[val_start+1:val_start+5])[0]
                val_end = val_start + 5
            else: break
        else:
            null_pos = data.find(b'\x00', val_start, end_pos)
            if null_pos != -1:
                val = data[val_start:null_pos].decode('cp1251', errors='replace').strip('\x00')
                val_end = null_pos + 1
            else:
                next_marker = data.find(b'\xe1', val_start, end_pos)
                if next_marker != -1:
                    val = data[val_start:next_marker].decode('cp1251', errors='replace').strip('\x00')
                    val_end = next_marker
                else:
                    val = data[val_start:min(val_start + 64, end_pos)].decode('cp1251', errors='replace').strip('\x00')
                    val_end = val_start + 64
        if idx < len(field_names): results[field_names[idx]] = val
        else: results[f"UNKNOWN_IDX_{idx}"] = val
        curr = val_end
    return results, "Success"
def get_structural_data(raw):
    if not creo_tree_reader: return {"error": "creo_tree_reader not available"}
    tree = creo_tree_reader.get_tree_dict(raw)
    out = {"family_table": [], "assembly_links": [], "relations": [], "drawing_info": {"source_models": [], "sheets": [], "format": ""}, "mfg_info": {"operation_id": "", "workpiece": ""}}
    for section in tree.get("sections", []):
        name, content = section.get("name"), section.get("content", [])
        if name == "FamilyInf":
            sec_offset, sec_len = section.get("offset"), section.get("len")
            if sec_offset is not None:
                sec_raw = raw[sec_offset : sec_offset + sec_len]
                for m in re.finditer(rb"user_instances\x00([\x20-\x7e]{1,40})\x00", sec_raw):
                    inst = m.group(1).decode("utf-8", "replace")
                    m_gen = re.search(rb"user_visible_name\x00([\x20-\x7e]{1,40})\x00", sec_raw)
                    gen = m_gen.group(1).decode("utf-8", "replace") if m_gen else "UNKNOWN"
                    out["family_table"].append({"generic": gen, "instance": inst})
        elif name == "MdlRefInfo":
            sec_offset, sec_len = section.get("offset"), section.get("len")
            if sec_offset is not None:
                sec_raw = raw[sec_offset : sec_offset + sec_len]
                for m in re.finditer(rb"([a-zA-Z0-9_]{3,30})\x00([\x20-\x7e]{1,64})\x00", sec_raw):
                    val = m.group(2).decode("utf-8", "replace")
                    if any(ext in val.upper() for ext in (".PRT", ".ASM")): out["assembly_links"].append(val)
        elif name == "LargeText":
            for m in re.finditer(rb"(/\\*if|/\\*else|/\\*endif)[\s\S]*?\x00", raw):
                rel = m.group(0).decode("utf-8", "replace").strip('\x00')
                if rel and rel not in out["relations"]: out["relations"].append(rel)
        elif name == "DwgData":
            drw = extract_drw_fields(raw)
            out["drawing_info"].update(drw)
            for m in re.finditer(rb"model_names<([A-Z][A-Za-z0-9_]+)\.PRT", raw):
                out["drawing_info"]["source_models"].append(m.group(1).decode("ascii"))
        elif name == "NeuAsmSld" and b"ASSEMBLY/ASSEM_MFG" in raw[:200]:
             m_op = re.search(rb"operation_id\x00([\x20-\x7e]{1,40})\x00", raw)
             if m_op: out["mfg_info"]["operation_id"] = m_op.group(1).decode("utf-8", "replace")
             m_wp = re.search(rb"workpiece\x00([\x20-\x7e]{1,40})\x00", raw)
             if m_wp: out["mfg_info"]["workpiece"] = m_wp.group(1).decode("utf-8", "replace")
    return out

def extract_family_info(raw):
    data = get_structural_data(raw)
    return data.get("family_table", [])

def extract_drw_fields(raw):
    data = get_structural_data(raw)
    return data.get("drawing_info", {"sheets": [], "format": ""})

def extract_mfg_fields(raw):
    data = get_structural_data(raw)
    return data.get("mfg_info", {"operation_id": "", "workpiece": ""})







