# -*- coding: utf-8 -*-
r"""creo_read  ЕДИНЫЙ САМОДОСТАТОЧНЫЙ ЧИТАТЕЛЬ ФАЙЛОВ CREO В ЛОБ (V181)."""
import datetime
import os
import re
import struct
from collections import Counter

TAIL = re.compile(rb"\xf7(.)\xe3([0-9]{1,7})\x00\x00(.{0,220}?)\x00((?:Creo )?[0-9][0-9.]*)\x00", re.S)
STAMP = re.compile(rb"\xf7\x14([\x20-\x7e\xc0-\xff]{1,24}?)\x00\xe2(.)(.)(.)(.)(.)(.)", re.S)
NAME_B = re.compile(rb"[\x00-\x1f\x80-\xff]([A-Za-z0-9][A-Za-z0-9_\-\.]{3,47}\.(?:PRT|ASM))", re.IGNORECASE)

def clean_creo_font(s: str) -> str:
    if not s:
        return ""
    return s.replace("\x01n\x02", "Ø").replace("\x01$", "").replace("\x01", "").replace("\x02", "")

def smart_decode(data: bytes) -> str:
    if not data:
        return ""
    clean = data.strip(b"\x00\x13\x19\x1b\x1e\xe3\xe0\xe1\xe2\xf6\xf7\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x1c")
    if not clean:
        return ""
    try:
        s = clean.decode("utf-8")
    except UnicodeDecodeError:
        s = clean.decode("cp1251", errors="replace")
    return clean_creo_font(s).strip()

def smart_decode_strip(data: bytes) -> str:
    return smart_decode(data).strip("\x00")

def stem(name: str) -> str:
    n = (name or "").upper()
    # V195: набор расширений = как в `plm_scanner.path_parts` (было упущено `.XPR` и вспомогательные):
    # из-за этого `engine.do_scan` (s = stem(basename)) писал `params.model`/`links.parent` для `.xpr`
    # С расширением («ER20-A.XPR»), тогда как `snapshots.model` — без него («ER20-A») ⇒ 387 835 «фантомов».
    for ext in (".PRT", ".ASM", ".DRW", ".MFG", ".NEU", ".SEC", ".M_P",
                ".XPR", ".TPH", ".CRC", ".IDX", ".STK", ".DSN", ".MRD", ".PDF", ".FRM", ".LAY",
                ".PRT.", ".ASM."):
        if ext in n:
            n = n.split(ext).pop(0)
            break
    return re.sub(r"\.\d+$", "", n)

def canon_model(s) -> str:
    """ЕДИНЫЙ КАНОН ИМЕНИ МОДЕЛИ (V193): stem → отбросить обрывки → UPPER.

    ЗАЧЕМ: замер по базе шары — `snapshots.model` хранился СТРОЧНЫМИ, а `links.child`/`params.model`
    ПРОПИСНЫМИ ⇒ 910 127 строк `params` и 142 774 `links` числились «висячими», хотя это одни и те же
    изделия. Здесь — ОДНА точка правды; все писатели зовут `canon_model`.
    ⚠️ SQLite `upper()` в этой сборке ASCII-only (ICU нет) — регистр поднимает Python, не SQL.
    """
    try:
        t = stem(str(s or "").strip())
    except Exception:
        t = str(s or "").strip()
    t = (t or "").strip().rstrip(".").strip()   # V206: снять хвостовую точку-артефакт («0-2500.»)
    if not t or t.startswith("-"):      # обрывок парсера («-00», «-001-002.PRT»): не имя модели
        return ""
    return t.upper()


def read(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()

def parse_toc(raw: bytes) -> dict:
    fsize = len(raw)
    out = {}
    entry_re = re.compile(
        rb"(?:^|[\r\n\x00])([A-Za-z0-9_:#.-]{2,64})\s+"
        rb"([0-9a-fA-F]{2,8})\s+([0-9a-fA-F]{1,8})\s+([0-9a-fA-F]{1,8})\s+"
        rb"(\d{3,5})\s+(-?\d+)\s+(-?\d+)\s+([0-9a-fA-F]{4})\s+([0-9a-fA-F]{4})"
    )
    for m in re.finditer(rb"#UGC_TOC", raw):
        chunk = raw[m.start():min(fsize, m.start() + 16384)]
        for em in entry_re.finditer(chunk):
            name = em.group(1).decode("ascii", "ignore")
            off = int(em.group(2), 16)
            ln = int(em.group(3), 16)
            if off + ln <= fsize and name != "NEXT_TOC_ENTRY" and name not in out:
                out[name] = (off, max(ln, 1))
    return out

def real(raw: bytes, key: str):
    m = re.search(rb"\xe0\x02" + key.encode("ascii", "ignore") + rb"\x00\xed", raw)
    if not m or m.end() + 8 > len(raw):
        return None
    try:
        val, = struct.unpack(">d", raw[m.end():m.end() + 8])
        return val
    except Exception:
        return None

def read_creo_num(buf: bytes, pos: int):
    if pos >= len(buf):
        return 0, None
    tag = buf[pos]
    if tag in (0x28, 0x9B):
        return 1, 0.0
    if tag == 0xED and pos + 9 <= len(buf):
        try:
            val, = struct.unpack(">d", buf[pos + 1:pos + 9])
            if abs(val) < 1e12:
                return 9, val
        except Exception:
            pass
        return 9, None
    if tag in (0x2F, 0x48) and pos + 3 <= len(buf):
        b1, b2 = buf[pos + 1], buf[pos + 2]
        E = (b1 >> 4) & 0x0F
        F = ((b1 & 0x0F) << 8) | b2
        val = (2.0 ** (E + 1)) * (1.0 + F / 4096.0)
        return 3, (-val if tag == 0x48 else val)
    if tag in (0x2D, 0x46) and pos + 8 <= len(buf):
        b1, b2 = buf[pos + 1], buf[pos + 2]
        E = (b1 >> 4) & 0x0F
        F_hi = ((b1 & 0x0F) << 8) | b2
        F_lo = int.from_bytes(buf[pos + 3:pos + 8], "big")
        val = (2.0 ** (E + 1)) * (1.0 + (F_hi + F_lo / float(1 << 40)) / 4096.0)
        return 8, (-val if tag == 0x46 else val)
    return 1, None

def outline_bbox_mm(raw: bytes):
    m = re.search(rb"outline\x00\xf9\x02\x03(.{48})", raw, re.S)
    if not m:
        return None
    buf = m.group(1)
    pos, nums = 0, []
    while len(nums) < 6 and pos < len(buf):
        st, v = read_creo_num(buf, pos)
        if v is not None:
            nums.append(v)
        pos += st
    if len(nums) == 6:
        xmin, ymin, zmin, xmax, ymax, zmax = nums
        dx, dy, dz = round(abs(xmax - xmin), 2), round(abs(ymax - ymin), 2), round(abs(zmax - zmin), 2)
        if 0 < max(dx, dy, dz) < 1e6:
            return (dx, dy, dz)
    return None
def params(raw: bytes, toc=None) -> dict:
    out = {}
    if toc is None:
        toc = parse_toc(raw)
    chunks = []
    if "LargeText" in toc:
        off, ln = toc["LargeText"]
        chunks.append(raw[off:off + ln])
    if "NeuPrtSld" in toc:
        off, ln = toc["NeuPrtSld"]
        chunks.append(raw[off:off + ln])
    if not chunks:
        chunks.append(raw)
    param_re = re.compile(rb"\xe3([A-Za-z_\x80-\xff][A-Za-z0-9_\x80-\xff]{1,60})\x00([^\xe3]{1,24}?)\xe3(.)([^\x00]{1,160}?)\x00")
    for ch in chunks:
        for m in param_re.finditer(ch):
            name = smart_decode(m.group(1))
            ptype = m.group(3)
            payload = m.group(4)
            if not name or name in out or "\ufffd" in name:
                continue
            if re.match(r"^Rz\d+$", name, re.I):
                continue
            if name.startswith(("PRO_MP_", "PTC_UNITS", "PTC_FAILURE_", "PTC_FATIGUE_", "PTC_INITIAL_BEND_", "PTC_MATERIAL_SUB_TYPE")):
                continue
            if name.startswith("Rz") and name[2:].isdigit():
                continue
            if ptype == b"3":
                val = smart_decode(payload)
                if val and val != "value(s_val)" and "\ufffd" not in val:
                    out[name] = " ".join(val.split())
            elif ptype == b"2" and len(payload) >= 8:
                try:
                    num, = struct.unpack(">d", payload[:8])
                    if abs(num) < 1e15:
                        out[name] = str(round(num, 6)).rstrip("0").rstrip(".")
                except Exception:
                    pass
    return out

def param(raw: bytes, names_list, default="") -> str:
    if isinstance(names_list, str):
        names_list = [names_list]
    pr = params(raw)
    upper = {k.upper(): v for k, v in pr.items()}
    for nm in names_list or ():
        k = (nm or "").strip()
        if not k:
            continue
        v = pr.get(k) or upper.get(k.upper())
        if v:
            return str(v)
    return default

def compose(raw: bytes, rule: str) -> str:
    if not rule:
        return ""
    pr = params(raw)
    upper = {k.upper(): v for k, v in pr.items()}
    out, i, n = [], 0, len(rule)
    while i < n:
        c = rule[i]
        if c == "{":
            j = rule.find("}", i)
            if j < 0:
                break
            key = rule[i + 1:j].strip()
            val = pr.get(key) or upper.get(key.upper()) or ""
            if val:
                out.append(str(val))
            i = j + 1
        elif c == '"':
            j = rule.find('"', i + 1)
            if j < 0:
                break
            out.append(rule[i + 1:j])
            i = j + 1
        elif c == "+":
            i += 1
        elif c.isspace():
            out.append(" ")
            i += 1
        else:
            j = i
            while j < n and rule[j] not in '{+"':
                j += 1
            out.append(rule[i:j])
            i = j
    return " ".join("".join(out).split())

_SOF = {0xC0, 0xC1, 0xC2, 0xC3}

def jpeg_size(blob: bytes):
    i, n = 2, len(blob)
    while i + 4 < n:
        if blob[i] != 0xFF:
            break
        mk = blob[i + 1]
        if mk in (0xD8, 0xD9) or (0xD0 <= mk <= 0xD7):
            i += 2
            continue
        ln = (blob[i + 2] << 8) | blob[i + 3]
        if mk in _SOF and i + 9 <= n:
            h = (blob[i + 5] << 8) | blob[i + 6]
            w = (blob[i + 7] << 8) | blob[i + 8]
            return w, h
        i += 2 + ln
    return 0, 0

def _find_jpg(raw: bytes):
    out, pos = [], 0
    while True:
        s = raw.find(b"\xff\xd8\xff", pos)
        if s < 0: break
        e = raw.find(b"\xff\xd9", s + 4)
        if e < 0: break
        blob = raw[s:e + 2]
        if 500 <= len(blob) <= 2_000_000:
            w, h = jpeg_size(blob)
            if w >= 32 and h >= 32:
                out.append((blob, "jpg"))
        pos = e + 2
    return out

def _find_bmp(raw: bytes):
    out, pos = [], 0
    while True:
        s = raw.find(b"BM", pos)
        if s < 0 or s + 26 > len(raw): break
        fsize, res1, res2, off = struct.unpack_from("<IHHI", raw, s + 2)
        if res1 == 0 and res2 == 0 and 54 <= off < fsize <= 4_000_000 and s + fsize <= len(raw):
            w, h = struct.unpack_from("<ii", raw, s + 18)
            if 32 <= abs(w) <= 4000 and 32 <= abs(h) <= 4000:
                out.append((raw[s:s + fsize], "bmp"))
                pos = s + fsize
                continue
        pos = s + 2
    return out

def cut_preview(raw: bytes, want="all"):
    if not raw: return []
    res = []
    if want in ("all", "jpg", "pict"): res.extend(_find_jpg(raw))
    if want in ("all", "bmp", "draw"): res.extend(_find_bmp(raw))
    return res

def role(raw: bytes, stems=frozenset(), me=""):
    if b"ASSEM_MFG" in raw[:400]: return "MFG"
    if b"MERGE_BASE_PART" in raw:
        m = re.search(rb"MERGE_BASE_PART.{0,80}?([A-Za-z0-9_\-]{5,40})\x00", raw, re.S)
        base = m.group(1).decode("latin-1") if m else ""
        if base and base.upper() not in ("MM_ASSY", "MM_PART"): return "nasled." + base
    for m in re.finditer(rb"ref_part_tab\x00", raw):
        nm = re.search(rb"name\x00([A-Za-z0-9_\-\.]{4,47})\x00", raw[m.end():m.end() + 200])
        if nm:
            s = stem(nm.group(1).decode("latin-1"))
            if s != me and (not stems or s in stems): return "proizv." + nm.group(1).decode("latin-1")
    return ""

def user_time(raw: bytes):
    out = []
    for m in STAMP.finditer(raw):
        s, mi, h, d, mo, y = (b for b in m.groups()[1:])
        try: dt = datetime.datetime(1900 + y, mo + 1, d, h, mi, s)
        except ValueError: continue
        if 1990 <= dt.year <= 2030:
            try: who = m.group(1).decode("utf-8")
            except UnicodeDecodeError: who = m.group(1).decode("cp1251", "replace")
            out.append((m.start(), who, dt))
    return sorted(set(out))

def last_hist(raw: bytes):
    st, last = user_time(raw), None
    for t in TAIL.finditer(raw):
        prev = [s for s in st if s[0] < t.start()]
        if prev:
            last_s = prev.pop()
            last = (t.group(2).decode(), last_s[1], last_s[2].strftime("%d.%m.%y %H:%M"))
        else:
            last = (t.group(2).decode(), "", "")
    return last

def names(raw: bytes):
    c = Counter()
    for m in NAME_B.finditer(raw):
        c[stem(m.group(1).decode("latin-1"))] += 1
    return c

def get_structural_data(raw: bytes) -> dict:
    return {"outline_mm": outline_bbox_mm(raw), "params": params(raw)}

def extract_family_info(raw: bytes): return []
def extract_drw_fields(raw: bytes): return {"sheets": [], "format": ""}
def extract_mfg_fields(raw: bytes): return {"operation_id": "", "workpiece": ""}