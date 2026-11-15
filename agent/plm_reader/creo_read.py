# -*- coding: utf-8 -*-
"""creo_read — PART 1 (Fixed Decoding & Family/LargeText)"""

import datetime
import os
import re
import struct
from collections import Counter

try:
    import creo_tree_reader
except ImportError:
    creo_tree_reader = None

def smart_decode(data):
    """Декодирует данные: сначала UTF-8, если ошибка — cp1251."""
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        try:
            return data.decode('cp1251')
        except UnicodeDecodeError:
            return data.decode('ascii', errors='replace')

def smart_decode_strip(data):
    """Декодирует и удаляет NUL-байты."""
    return smart_decode(data).strip('\x00')

TAIL = re.compile(rb"\xf7(.)\xe3([0-9]{1,7})\x00\x00(.{0,220}?)\x00((?:Creo )?[0-9][0-9.]*)\x00", re.S)
STAMP = re.compile(rb"\xe1\xf6\xe1([\x20-\x7e\xc0-\xff]{1,24}?)\x00\xe2(.)(.)(.)(.)(.)(.)", re.S)
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
        name = smart_decode_strip(data[curr:null_pos])
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
        else: # String/Variable
            next_marker = data.find(b'\xe1', val_start, end_pos)
            if next_marker != -1:
                val = smart_decode_strip(data[val_start:next_marker])
                val_end = next_marker
            else:
                val = smart_decode_strip(data[val_start:min(val_start + 64, end_pos)])
                val_end = val_start + 64
                
        if idx < len(field_names): results[field_names[idx]] = val
        else: results[f"UNKNOWN_IDX_{idx}"] = val
        curr = val_end
        
    return results, "Success"
def get_structural_data(raw):
    if not creo_tree_reader: return {"error": "creo_tree_reader not available"}
    tree = creo_tree_reader.get_tree_dict(raw)
    out = {
        "family_table": [], 
        "assembly_links": [], 
        "relations": [], 
        "drawing_info": {"source_models": [], "sheets": [], "format": ""}, 
        "mfg_info": {"operation_id": "", "workpiece": ""},
        "family_parameters": {},
        "large_text_parameters": {},
        "equations": []
    }
    
    for section in tree.get("sections", []):
        name, content = section.get("name"), section.get("content", [])
        
        if name == "FamilyInf":
            sec_offset, sec_len = section.get("offset"), section.get("len")
            if sec_offset is not None:
                sec_raw = raw[sec_offset : sec_offset + sec_len]
                
                # 1. Extract instances
                for m in re.finditer(rb"user_instances\x00([^\x00]+)\x00", sec_raw):
                    inst = smart_decode_strip(m.group(1))
                    out["family_table"].append({"instance": inst})
                
                # 2. Extract Sld_FamilyInfo (Parameters/Mass)
                dict_start = sec_raw.find(b'\xe1\xe0')
                if dict_start != -1:
                    params, msg = parse_record_flow(sec_raw, 0)
                    if msg == "Success":
                        out["family_parameters"].update(params)

        elif name == "MdlRefInfo":
            sec_offset, sec_len = section.get("offset"), section.get("len")
            if sec_offset is not None:
                sec_raw = raw[sec_offset : sec_offset + sec_len]
                for m in re.finditer(rb"([A-Za-z0-9_.-]{3,30})\x00([^\x00]{1,64})\x00", sec_raw):
                    val = smart_decode_strip(m.group(2))
                    if any(ext in val.upper() for ext in (".PRT", ".ASM")):
                        out["assembly_links"].append(val)

        elif name == "LargeText":
            # 1. Equations (/*if ...)
            for m in re.finditer(rb"((?:/\*if|/\*else|/\*endif)[^\\x00]+)", raw):
                eq = smart_decode_strip(m.group(1))
                if eq and eq not in out["relations"]:
                    out["relations"].append(eq)
                    out["equations"].append(eq)
            
            # 2. Parameters (symtbl / alt_symtbl)
            sec_offset, sec_len = section.get("offset"), section.get("len")
            if sec_offset is not None:
                sec_raw = raw[sec_offset : sec_offset + sec_len]
                dict_start = sec_raw.find(b'\xe1\xe0')
                if dict_start != -1:
                    params, msg = parse_record_flow(sec_raw, 0)
                    if msg == "Success":
                        out["large_text_parameters"].update(params)

        elif name == "DwgData":
            drw = extract_drw_fields(raw)
            out["drawing_info"].update(drw)
            for m in re.finditer(rb"model_names<([A-Z][A-Za-z0-9_]+)\.PRT", raw):
                out["drawing_info"]["source_models"].append(m.group(1).decode("ascii"))

        elif name == "NeuAsmSld" and b"ASSEMBLY/ASSEM_MFG" in raw[:200]:
             m_op = re.search(rb"operation_id\x00([^\x00]+)\x00", raw)
             if m_op: out["mfg_info"]["operation_id"] = smart_decode_strip(m_op.group(1))
             m_wp = re.search(rb"workpiece\x00([^\x00]+)\x00", raw)
             if m_wp: out["mfg_info"]["workpiece"] = smart_decode_strip(m_wp.group(1))

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
