import os
import re
import json
import time
import struct

def smart_decode(raw_bytes: bytes) -> str:
    clean = raw_bytes.strip(b'\x00\x13\x19\x1b\x1e\xe3\xe0\xe1\xe2\xf6\xf7\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x1c')
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
        rb'([^\xe3]{1,24}?)\xe3(.)([^\x00]{1,160}?)\x00'
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
            if is_drw and len(val) > 1 and val[:1] in ('?', '>', 'A', '+', 'C'):
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

def extract_family_table(family_raw: bytes) -> dict:
    if not family_raw:
        return {"total_instances": 0, "instances": []}
    inst_re = re.compile(rb'\xe3\x02([A-Za-z0-9_.-]{3,60})\x00')
    instances = []
    skip = {'LIST', 'Defaults', 'STEEL_45', 'METRIC', 'DEFAULT'}
    for m in inst_re.finditer(family_raw):
        val = smart_decode(m.group(1))
        if val and val not in skip and not val.startswith(('PRO_MP_', '_')) and val not in instances:
            instances.append(val)
    return {"total_instances": len(instances), "instances": instances[:25]}

def extract_asm_bom_and_refs(sections: dict, self_base: str) -> tuple:
    refs = []
    rev_guids = []
    bom_counts = {}

    mdl_status = sections.get('MdlStatus', b'')
    if mdl_status:
        comp_re = re.compile(rb'\xe2(?:[\xf7].)?([A-Za-z0-9_.-]{3,60}\.(?:PRT|ASM|prt|asm))\x00.{0,180}?\xd0\xba\xd0\xbe\xd0\xbc\xd0\xbf\xd0\xbe\xd0\xbd\xd0\xb5\xd0\xbd\xd1\x82 id (\d+)', re.DOTALL)
        seen_ids = set()
        for m in comp_re.finditer(mdl_status):
            cname_bytes = m.group(1)
            if len(cname_bytes) > 1 and ord(cname_bytes[0]) == len(cname_bytes[1:]) + 1:
                cname_bytes = cname_bytes[1:]
            cname = smart_decode(cname_bytes).upper()
            cid = m.group(2).decode('ascii')
            if cname.rsplit('.', 1)[0].lower() == self_base.lower():
                continue
            if (cname, cid) not in seen_ids:
                seen_ids.add((cname, cid))
                bom_counts[cname] = bom_counts.get(cname, 0) + 1

    for sec_name in ('MdlStatus', 'MdlRefInfo', 'BasBasData', 'DwgData', 'FeatDefs', 'AllFeatur', 'NeuAsmSld'):
        chunk = sections.get(sec_name, b'')
        if not chunk:
            continue
        for m in re.finditer(rb'(?:^|[\x00-\x1f\xe0-\xff])([A-Za-z0-9_.-]{3,60}\.(?:PRT|ASM|DRW|MFG|prt|asm|drw|mfg))(?=\x00|[\r\n]|\xe3)', chunk):
            ref = smart_decode(m.group(1))
            if not ref:
                continue
            stem = ref.rpartition('.')[0]
            if stem.lower() == self_base.lower():
                continue
            if stem.lower() in ('mm_part', 'mm_assy', 'sborka_mm', 'blk0001', 'inlbs_part_bulk_abs', 'inlbs_mfg_nc', 'mfg_nc_new', 'sborka_mfg'):
                continue
            if re.fullmatch(r'[0-9A-Fa-f]{28,32}', stem):
                if ref not in rev_guids:
                    rev_guids.append(ref)
                continue
            if ref not in refs:
                refs.append(ref)

    return refs, bom_counts, rev_guids

def extract_mfg_sequences(data: bytes) -> dict:
    seqs = []
    tools = []
    for m in re.finditer(rb'\xe2(?:[\xf7].)?([A-Za-z0-9_\x80-\xff.-]{3,60})\x00.{0,60}?(?:NC_SEQUENCE|MILLING|TURNING|DRILLING|TRAJECTORY|FACE|VOLUME|PROFILE|THREAD)', data, re.DOTALL):
        s = smart_decode(m.group(1))
        if s and len(s) >= 3 and s not in seqs:
            seqs.append(s)
    for m in re.finditer(rb'(?:TOOL_ID|TOOL_NAME|CUTTER_NAME)\x00[^\x00]{1,16}?\xe3([^\x00]{1,60})\x00', data):
        t = smart_decode(m.group(1))
        if t and t not in tools:
            tools.append(t)
    return {"nc_sequences": seqs[:30], "tools": tools[:20]}

def parse_creo_file(filepath: str, rel_folder: str = "", direction: str = "") -> dict:
    with open(filepath, 'rb') as f:
        data = f.read()

    fname = os.path.basename(filepath)
    ext_m = re.search(r'\.(prt|asm|drw|mfg)(?:\.\d+)?$', fname, re.I)
    ext = ext_m.group(1).lower() if ext_m else "unknown"
    self_base = re.sub(r'\.(prt|asm|drw|mfg)(?:\.\d+)?$', '', fname, flags=re.I)

    sections = split_sections(data)
    large_raw = sections.get('LargeText', b'')
    fam_raw = sections.get('FamilyInf', b'')

    params = extract_symtbl_params(large_raw, is_drw=(ext == 'drw'))
    refs, bom_counts, rev_guids = extract_asm_bom_and_refs(sections, self_base)

    res = {
        "direction": direction,
        "folder": rel_folder,
        "file": fname,
        "type": ext.upper(),
        "size_kb": round(len(data) / 1024, 1),
        "sections_count": len(sections),
        "parameters": params,
        "references": refs
    }
    if bom_counts:
        res["asm_bom_qty"] = bom_counts
    ft = extract_family_table(fam_raw)
    if ft["total_instances"] > 0:
        res["family_table"] = ft
    if ext == 'mfg' or params.get('ТИП') == 'Производство' or params.get('ТИП2') == 'Технология':
        mfg = extract_mfg_sequences(data)
        if mfg["nc_sequences"] or mfg["tools"]:
            res["mfg_details"] = mfg
    if rev_guids:
        res["revision_guids_count"] = len(rev_guids)
    return res

if __name__ == "__main__":
    t0 = time.perf_counter()
    directions = [
        ("ЦТКД Электон", r"Z:\PTC\Work\001_15 ЦТКД Электон"),
        ("DF Держатели форм", r"Z:\PTC\Work\000_51 DF Держатели форм"),
        ("Модельная оснастка для литья", r"Z:\PTC\Work\000_03 401-LIT Литейное производство\000_5 401-LIT-MO Модельная оснастка для литья")
    ]
    out_file = r"D:\AI\PROBA\3_directions_report.txt"

    total_all_files = 0
    total_all_bytes = 0
    latest_map = {}

    for dir_label, root_dir in directions:
        if not os.path.exists(root_dir):
            continue
        for cur_root, _, files in os.walk(root_dir):
            rel = os.path.relpath(cur_root, root_dir)
            for f in files:
                full_p = os.path.join(cur_root, f)
                try:
                    fsize = os.path.getsize(full_p)
                except OSError:
                    fsize = 0
                total_all_files += 1
                total_all_bytes += fsize

                m = re.match(r'^(.+\.(?:prt|asm|drw|mfg))(?:\.(\d+))?$', f, re.I)
                if m:
                    base_key = (cur_root, m.group(1).lower())
                    rev = int(m.group(2)) if m.group(2) else 0
                    if base_key not in latest_map or rev > latest_map[base_key][0]:
                        latest_map[base_key] = (rev, full_p, rel, fsize, dir_label)

    results = []
    parsed_bytes = 0
    for _, (_, full_p, rel, fsize, dir_label) in sorted(latest_map.items()):
        parsed_bytes += fsize
        try:
            results.append(parse_creo_file(full_p, rel, dir_label))
        except Exception as e:
            results.append({"direction": dir_label, "folder": rel, "file": os.path.basename(full_p), "error": str(e)})

    elapsed = round(time.perf_counter() - t0, 2)
    parsed_mb = round(parsed_bytes / (1024 * 1024), 2)
    total_mb = round(total_all_bytes / (1024 * 1024), 2)
    speed = round(parsed_mb / elapsed, 2) if elapsed > 0 else 0

    report = {
        "summary": {
            "directions_scanned": [d[0] for d in directions],
            "elapsed_sec": elapsed,
            "total_files_in_tree": total_all_files,
            "total_size_all_mb": total_mb,
            "latest_creo_models_parsed": len(results),
            "parsed_models_size_mb": parsed_mb,
            "throughput_mb_per_sec": speed
        },
        "models": results
    }

    with open(out_file, "w", encoding="utf-8") as out:
        json.dump(report, out, ensure_ascii=False, indent=2)

    print(f"DONE_3_DIRS | Time: {elapsed}s | All files: {total_all_files} ({total_mb} MB) | Latest models: {len(results)} ({parsed_mb} MB) | Speed: {speed} MB/s")