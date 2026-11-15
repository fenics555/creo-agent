import sys
import os
import re
import json
import struct

def smart_decode(raw_bytes: bytes) -> str:
    clean = raw_bytes.strip(b'\x00\x13\xe3\xe0\xe1\xe2\xf6\xf7\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x1c')
    if not clean:
        return ""
    try:
        return clean.decode('utf-8')
    except UnicodeDecodeError:
        return clean.decode('cp1251', errors='replace')

def split_sections(data: bytes) -> dict:
    pattern = re.compile(rb'(?:^|[\r\n\x00])#([A-Z][A-Za-z0-9_]{4,40})(?=[\r\n\x00])')
    matches = list(pattern.finditer(data))
    sections = {}
    for i, m in enumerate(matches):
        name = m.group(1).decode('ascii', errors='ignore')
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(data)
        sections[name] = data[start:end]
    return sections

def extract_symtbl_params(large_text_raw: bytes, is_drw: bool = False) -> dict:
    params = {}
    param_re = re.compile(
        rb'\xe3([A-Za-z_\x80-\xff][A-Za-z0-9_\x80-\xff]{1,60})\x00'
        rb'([^\xe3]{1,24}?)\xe3([234])([^\x00]{1,160}?)\x00'
    )
    for m in param_re.finditer(large_text_raw):
        name = smart_decode(m.group(1))
        ptype = m.group(3)
        payload = m.group(4)
        if not name or name.startswith(('PRO_MP_TRF', 'PTC_UNITS')):
            continue
        if ptype == b'3':
            if is_drw and len(payload) > 1 and ord(payload[:1]) == len(payload) - 1:
                payload = payload[1:]
            val = smart_decode(payload)
            if is_drw and len(val) > 1 and val[:1] in ('?', '>', 'A'):
                val = val[1:]
            params[name] = val
        elif ptype == b'2' and len(payload) >= 8:
            try:
                num = struct.unpack('>d', payload[:8])[0]
                if abs(num) < 1e15:
                    params[name] = round(num, 6)
            except Exception:
                pass
        elif ptype == b'4' and len(payload) >= 4:
            try:
                params[name] = struct.unpack('>i', payload[:4])[0]
            except Exception:
                pass
    return params

def extract_relations(large_text_raw: bytes) -> list:
    relations = []
    rel_re = re.compile(rb'(?:/\*[^\x00\r\n]{2,140}|\b(?:IF|ELSE|ENDIF)\b[^\x00\r\n]{0,100})')
    for m in rel_re.finditer(large_text_raw):
        line = smart_decode(m.group(0))
        if len(line) > 2 and line not in relations:
            relations.append(line)
    return relations[:20]

def extract_family_table(family_raw: bytes) -> dict:
    if not family_raw:
        return {"total_instances": 0, "instances": [], "columns": []}
    name_tag_re = re.compile(rb'(?:\xe0\x0aname\x00|\xe3)([^\x00\r\n]{2,60})\x00')
    instances = []
    columns = []
    skip = {'name', 'LIST', 'Defaults', 'STEEL_45', 'METRIC', 'DEFAULT', 'PRO_MP_CSYS', 'PRO_MP_ALT_CSYS'}
    for m in name_tag_re.finditer(family_raw):
        token = smart_decode(m.group(1))
        if not token or token in skip or token.startswith(('PRO_MP_', '_')):
            continue
        if re.search(r'(?:DIN|GOST|ISO|M\d+)[-_A-Za-z0-9.]+', token, re.IGNORECASE) and ('-' in token or 'X' in token or 'x' in token):
            if token not in instances:
                instances.append(token)
        elif re.match(r'^[A-ZА-ЯЁ_][A-ZА-ЯЁ0-9_]{1,40}$', token):
            if token not in columns:
                columns.append(token)
    return {"total_instances": len(instances), "instances": instances[:25], "columns": columns[:25]}

def extract_clean_refs(sections: dict, self_base: str) -> list:
    refs = []
    for sec_name in ('MdlRefInfo', 'BasBasData', 'DwgData', 'FeatDefs', 'AllFeatur', 'NeuAsmSld'):
        chunk = sections.get(sec_name, b'')
        if not chunk:
            continue
        for m in re.finditer(rb'(?:^|[\x00-\x1f\xe0-\xff])([A-Za-z0-9_.-]{3,60}\.(?:PRT|ASM|DRW|MFG|prt|asm|drw|mfg))(?=\x00|[\r\n])', chunk):
            ref = smart_decode(m.group(1))
            if not ref:
                continue
            stem = ref.rpartition('.')[0].lower()
            if stem == self_base.lower():
                continue
            if stem in ('mm_part', 'mm_assy', 'sborka_mm', 'blk0001', 'inlbs_part_bulk_abs'):
                continue
            if re.fullmatch(r'[0-9A-Fa-f]{28,32}', stem):
                continue
            if ref not in refs:
                refs.append(ref)
    return refs

def extract_mfg_info(data: bytes, ext: str) -> dict:
    if ext != 'mfg':
        return {}
    ops = []
    tools = []
    for m in re.finditer(rb'(?:\xe3|\x00)([A-Z0-9_.-]{3,50}(?:MILL|TURN|DRILL|FACE|ROUGH|FINISH|OP|FREZ|TOCH)[A-Z0-9_.-]{0,30})\x00', data, re.IGNORECASE):
        val = smart_decode(m.group(1))
        if val and val not in ops:
            ops.append(val)
    for m in re.finditer(rb'(?:TOOL_ID|TOOL_NAME)\x00[^\x00]{1,16}?\xe3([^\x00]{1,60})\x00', data):
        t = smart_decode(m.group(1))
        if t and t not in tools:
            tools.append(t)
    return {"operations": ops[:30], "tools": tools[:20]}

def extract_drw_info(sections: dict, ext: str) -> dict:
    if ext != 'drw':
        return {}
    dwg_raw = sections.get('DwgData', b'')
    formats = []
    for m in re.finditer(rb'([A-Za-z0-9_.-]{3,50}\.frm)', dwg_raw, re.IGNORECASE):
        f = smart_decode(m.group(1))
        if f and f not in formats:
            formats.append(f)
    return {"formats": formats}

def parse_creo_file(filepath: str) -> dict:
    with open(filepath, 'rb') as f:
        data = f.read()

    fname = os.path.basename(filepath)
    ext_m = re.search(r'\.(prt|asm|drw|mfg)(?:\.\d+)?$', fname, re.IGNORECASE)
    ext = ext_m.group(1).lower() if ext_m else "unknown"
    self_base = re.sub(r'\.(prt|asm|drw|mfg)(?:\.\d+)?$', '', fname, flags=re.IGNORECASE)

    sections = split_sections(data)
    large_raw = sections.get('LargeText', b'')
    fam_raw = sections.get('FamilyInf', b'')

    res = {
        "file": fname,
        "type": ext.upper(),
        "size_bytes": len(data),
        "sections_count": len(sections),
        "parameters": extract_symtbl_params(large_raw, is_drw=(ext == 'drw')),
        "references": extract_clean_refs(sections, self_base)
    }
    ft = extract_family_table(fam_raw)
    if ft["total_instances"] > 0 or ft["columns"]:
        res["family_table"] = ft
    if ext == 'mfg':
        res["mfg_details"] = extract_mfg_info(data, ext)
    if ext == 'drw':
        res["drw_details"] = extract_drw_info(sections, ext)
    rels = extract_relations(large_raw)
    if rels:
        res["relations_preview"] = rels
    return res

if __name__ == "__main__":
    target_dir = r"D:\AI\PROBA\models\23-1017GRI 2кап чистовой BDF 5 1_2''"
    out_file = r"D:\AI\PROBA\23-1017GRI_report.txt"

    results = []
    for root, _, files in os.walk(target_dir):
        for f in sorted(files):
            if re.search(r'\.(prt|asm|drw|mfg)(\.\d+)?$', f, re.IGNORECASE):
                full_p = os.path.join(root, f)
                results.append(parse_creo_file(full_p))

    with open(out_file, "w", encoding="utf-8") as out:
        json.dump(results, out, ensure_ascii=False, indent=2)
    print("V3_CLEAN_FILES:", len(results))