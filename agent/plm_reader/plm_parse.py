# -*- coding: utf-8 -*-
"""plm_parse.py — вынесено из plm_reader.py распилом (см. СПЕКА_РАСПИЛА_PLM_READER.md)."""
from plm_reader import (
    DIM_AFTER_RE,
    DIM_HEAD_RE,
    DIM_NAME_RE,
    DRW_MODEL_RE,
    PARAM_NUM_RE,
    TEXT_VALUE_RE,
    _NOTES_JUNK,
    os,
    re,
    struct,
)


MODELFILE = re.compile(r"\.([a-z_]{2,4})\.\d+$", re.IGNORECASE)
def read_bytes(path, limit_mb):
    if limit_mb and os.path.getsize(path) > limit_mb * 1_000_000:
        return None
    with open(path, "rb") as f:
        return f.read()
def sections(raw):
    """Внутреннее оглавление файла: {имя: (offset, length)}."""
    out, pos = {}, raw.find(b"#UGC_TOC")
    for _ in range(20):
        if pos < 0:
            break
        p = raw.find(b"\n", pos)
        nxt = -1
        while True:
            e = raw.find(b"\n", p + 1)
            if e < 0:
                break
            line = raw[p + 1:e].decode("ascii", "replace").strip()
            p = e
            if line.startswith("NEXT_TOC_ENTRY"):
                nxt = int(line.split()[1], 16)
                break
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_:]{1,40}) ([0-9a-f]{2,8}) ([0-9a-f]{2,8})"
                         r"(?: ([0-9a-f]{2,8}))?(.*)$", line)
            if m and (not m.group(5).strip() or m.group(5).strip()[0] in "0123456789-"):
                ln = int(m.group(4), 16) if m.group(4) else int(m.group(3), 16)
                out[m.group(1)] = (int(m.group(2), 16), max(ln, 1))
        if nxt < 0 or nxt >= len(raw):
            break
        pos = nxt
    return out
def real_value(raw, key):
    """Числовое поле изделия (объём, масса …). None, если не найдено."""
    m = re.search(rb"\xe0\x02" + re.escape(key.encode()) + rb"\x00\xed", raw)
    if not m or m.end() + 8 > len(raw):
        return None
    try:
        return struct.unpack(">d", raw[m.end():m.end() + 8])[0]
    except Exception:
        return None
def packed_at(raw, i):
    """Компактное число: (длина, значение) или None."""
    if i >= len(raw):
        return None
    b0 = raw[i]
    if b0 == 0x2D and i + 7 < len(raw):
        frac = raw[i + 3:i + 8]
        if all(0x20 <= x < 0x7F for x in frac):
            return None
        b1, b2 = raw[i + 1], raw[i + 2]
        E, F = b1 >> 4, ((b1 & 0x0F) << 8) | b2
        if E > 15:
            return None
        base = (2 ** (E + 1)) * (1 + F / 4096.0)
        step = (2 ** (E + 1)) / 4096.0
        return 8, base + (int.from_bytes(frac, "big") / float(1 << 40)) * step
    if b0 in (0x2F, 0x48) and i + 2 < len(raw):
        b1, b2 = raw[i + 1], raw[i + 2]
        E, F = b1 >> 4, ((b1 & 0x0F) << 8) | b2
        v = (2 ** (E + 1)) * (1 + F / 4096.0)
        return 3, (-v if b0 == 0x48 else v)
    if b0 == 0x2A and i + 2 < len(raw):
        b1, b2 = raw[i + 1], raw[i + 2]
        E, F = b1 >> 4, ((b1 & 0x0F) << 8) | b2
        return 3, (2 ** (E - 15)) * (1 + F / 4096.0)
    return None
def clean_name(s):
    return re.sub(r"[\x00-\x1f]+", " ", s).strip()
def parameters(raw, sec):
    """Параметры изделия: {имя: значение} (обозначение, наименование, материал …)."""
    out = {}
    for name in ("NeuPrtSld", "LargeText"):
        if name not in sec:
            continue
        off, ln = sec[name]
        chunk = raw[off:off + ln]
        for m in re.finditer(rb"([\x20-\xff]{3,32})\x00\xe2([\x32\x33])(.{0,60}?)\x00", chunk, re.S):
            t = re.search(r"[\w]+$", m.group(1).decode("utf-8", "replace"))
            if not t:
                continue
            key = t.group(0)
            if m.group(2)[0] == 0x33:
                try:
                    val = clean_name(m.group(3).decode("utf-8"))
                except UnicodeDecodeError:
                    continue
                if val:
                    out.setdefault(key, val)
            else:
                r = packed_at(m.group(3), 0) if m.group(3) else None
                if r:
                    out.setdefault(key, r[1])
    return out
def outline_mm(raw, sec):
    """Габарит изделия, мм."""
    for name in ("FullMData", "BasicText"):
        if name not in sec:
            continue
        off, ln = sec[name]
        chunk = raw[off:off + ln]
        m = re.search(rb"outline\x00", chunk)
        if not m:
            continue
        seg = chunk[m.end():m.end() + 12]
        vals = []
        for k in (4, 8):
            try:
                vals.append(abs(struct.unpack_from("<f", seg, k)[0]) / 1000.0)
            except Exception:
                pass
        vals = [v for v in vals if 0.001 <= v <= 100000.0]   # отсеять мусорные значения
        if vals:
            return vals
    return []
MDL_NAME_RE = re.compile(r"^[A-Za-z0-9А-Яа-яЁё_\-.? ]{4,80}\.(?:prt|asm|PRT|ASM)$")
def dwg_models(raw):
    """Из чёртежа (.drw): модели (детали/сборки), которые он показывает.

    Возвращает список имён файлов, напр. ['A887-94-1500-01.PRT'].
    В 75 % имён часть символов нечитаема ('?') — это потеря данных в самом файле Creo,
    последний компонент пути берётся как есть."""
    out = []
    if not raw or b"model_names" not in raw:
        return out
    for m in DRW_MODEL_RE.finditer(raw):
        try:
            nm = m.group(1).decode("utf-8")
        except UnicodeDecodeError:
            continue
        nm = nm.replace("/", "\\").split("\\")[-1]
        nm = " ".join(nm.split()).strip()
        if len(nm) < 4 or nm.endswith("?") or not MDL_NAME_RE.match(nm):
            continue
        if nm not in out:
            out.append(nm)
        if len(out) >= 8:
            break
    return out
def tech_notes(raw, limit=8):
    """Технические требования из секции Notes (`text_value\\0<текст>\\0`).

    Отсекаются служебные подписи (`RIGHT`, `PRT_CSYS_DEF`, `DTM1`, `\\поле\\`)
    — без этого в вывод идёт больше мусора, чем текста."""
    out = []
    if not raw or b"text_value" not in raw:
        return out
    for m in TEXT_VALUE_RE.finditer(raw):
        try:
            s = " ".join(m.group(1).decode("utf-8").split())
        except UnicodeDecodeError:
            continue                      # нечитаемый хвост — пропускаем
        if not (2 < len(s) < 500):
            continue
        if s.startswith("\\") or s.endswith("\\"):
            continue
        if _NOTES_JUNK.match(s):
            continue
        if not any(ch.isdigit() for ch in s):
            continue                      # слово без цифр — служебное имя вида
        if s not in out:
            out.append(s)
        if len(out) >= limit:
            break
    return out
def _dec_num(t):
    """Число после метки e2 32: 1 байт / 3 байта / 8 байт. None — не угадываем."""
    if not t:
        return None
    if t[0] == 0xF7:                     # служебный префикс
        t = t[1:]
        if not t:
            return None
    v = {0x18: 0.0, 0x07: 0.001, 0x0D: 0.25, 0x0E: 0.5, 0x0F: 1.0}.get(t[0])
    if v is not None:
        return v
    if len(t) >= 3 and t[0] in (0x2F, 0x48):
        # ⚠️ знак байта 0x2F на живых файлах означает «плюс» (THREAD_DIAMETER=+12 при М12),
        # поэтому знак выбираем по «круглости»: без минуса целое или кратное 0.5 → берём плюс
        E, F = (t[1] >> 4) & 0x0F, ((t[1] & 0x0F) << 8) | (t[2] & 0xFF)
        mag = (2.0 ** (E + 1)) * (1.0 + F / 4096.0)
        if abs(mag - round(mag)) < 1e-9 or abs(mag * 2 - round(mag * 2)) < 1e-9:
            return mag
        return -mag if t[0] == 0x2F else mag
    if len(t) >= 8 and t[0] == 0x2D:
        sign = -1 if t[1] & 0x80 else 1
        E, F = (t[1] >> 4) & 0x0F, t[1] & 0x0F
        frac = int.from_bytes(t[2:7], "big")
        return sign * (2.0 ** (E + 1)) * (1.0 + (F + frac / 2.0 ** 40) / 4096.0)
    if t[0] == 0xED and len(t) >= 9:      # прямой double за маркером
        try:
            v = struct.unpack(">d", t[1:9])[0]
            return v if 1e-9 < abs(v) < 1e9 else None
        except Exception:
            return None
    return None
def numeric_params(raw, limit=60):
    """Числовые параметры детали: {имя: число}.

    Имя = `\\xe3<ИМЯ>\\0\\xe2\\x32`, значение — за ним. Значения за служебными байтами
    не угадываются (лучше пусто, чем мусор в выводе)."""
    out = {}
    if not raw or b"\xe2\x32" not in raw:
        return out
    for m in PARAM_NUM_RE.finditer(raw):
        try:
            nm = m.group(1).decode("utf-8").strip()
        except UnicodeDecodeError:
            continue
        if not nm or not all(ch.isprintable() for ch in nm):
            continue
        v = _dec_num(raw[m.end():m.end() + 20])
        if v is not None and abs(v) < 1e7:
            out.setdefault(nm, round(v, 6))
        if len(out) >= limit:
            break
    return out
def _dec3_any(b):
    """3-байтовое число с ЛЮБЫМ маркером: 2^(E+1)*(1+F/4096)."""
    if len(b) < 3:
        return None
    E = (b[1] >> 4) & 0x0F
    F = ((b[1] & 0x0F) << 8) | b[2]
    return (2.0 ** (E + 1)) * (1.0 + F / 4096.0)
def _dec_ef(b):
    """Число БЕЗ маркера (в new_val блока diff_vals): [E:F12][дробная]."""
    if len(b) < 2:
        return None
    E = (b[0] >> 4) & 0x0F
    F = ((b[0] & 0x0F) << 8) | b[1]
    return (2.0 ** (E + 1)) * (1.0 + F / 4096.0)
def _dim_name(seg, kd):
    """Имя размера dNN после `dim_name` (префикс f2/f1 стоит ПОСЛЕ имени)."""
    for pref in (b"\xf2", b"\xf1"):
        p = seg.find(pref, kd, kd + 40)
        if p < 0:
            continue
        s, q = p + 1, p + 1
        while q < len(seg) and seg[q] != 0x00 and q - s < 40:
            q += 1
        cand = seg[s:q].decode("latin-1", "replace")
        if re.match(r"^d\d{1,5}$", cand):
            return cand
    return None
def read_dims_all(raw):
    """РАЗМЕРЫ детали {dNN: мм} — три источника (см. archive_scan.py).

    (а) значение ДО имени, (б) значение ПОСЛЕ имени, (в) `new_val` из diff_vals.
    Проверено эталоном a887-94-1500-01: d12=8, d13=21.5, d25=12.7."""
    out = {}
    if not raw:
        return out
    for m in DIM_HEAD_RE.finditer(raw):
        v = _dec3_any(raw[m.end():m.end() + 3])
        if v is None or not (0.001 < abs(v) < 1e6):
            continue
        mn = DIM_NAME_RE.search(raw[m.end() + 3:m.end() + 43])
        if mn:
            out.setdefault(mn.group(1).decode("latin-1"), round(v, 4))
    if len(out) < 3:
        for m in DIM_AFTER_RE.finditer(raw):
            v = _dec3_any(raw[m.end() + 8:m.end() + 11])
            if v is not None and 0.001 < abs(v) < 1e6:
                out.setdefault(m.group(1).decode("latin-1"), round(v, 4))
    out.update(read_history_vals(raw))
    return {k: v for k, v in out.items()
            if re.match(r"^d\d{1,5}$", k) and isinstance(v, (int, float))}
def read_history_vals(raw):
    """Текущее значение размера из `new_val` блока diff_vals: {dNN: мм}."""
    out = {}
    if not raw or b"diff_vals" not in raw:
        return out
    for m in re.finditer(rb"diff_vals", raw):
        seg = raw[m.end():m.end() + 260]
        kd, kn = seg.find(b"dim_name"), seg.find(b"new_val")
        if kd < 0 or kn < 0:
            continue
        nm = _dim_name(seg, kd)
        if not nm:
            continue
        c = seg[kn + 7:kd].lstrip(b"\x00") if kn < kd else b""
        while c[:1] in (b"\xf1", b"\xf7", b"\xe3"):
            c = c[1:]
        v = _dec_ef(c[:2])
        if isinstance(v, (int, float)):
            out.setdefault(nm, round(float(v), 4))
        if len(out) >= 100:
            break
    return out
def _hist_val(chunk):
    """Значение old_val/new_val: число | None (e1 = значения нет)."""
    if not chunk:
        return None
    c = chunk.lstrip(b"\x00")
    if not c or c[:1] == b"\xe1":
        return None
    if b"value(" in c:                       # record: type 2 / value(d_val) <число>
        tail = c[c.find(b"value("):]
        for i in range(0, max(1, min(len(tail) - 2, 24))):
            bb = tail[i:i + 3]
            if len(bb) >= 3 and bb[0] in (0x2F, 0x48):
                return round(_dec3_any(bb), 4)
        return None
    while c[:1] in (b"\xf1", b"\xf7", b"\xe3"):
        c = c[1:]
    v = _dec_ef(c[:2])
    return round(v, 4) if v is not None else None
def read_history(raw):
    """ИСТОРИЯ ИЗМЕНЕНИЙ РАЗМЕРОВ: [{name, old, new}] — «было → стало».

    Блок `diff_vals`: `old_val` (было) · `new_val` (стало) · `dim_name` (dNN).
    Это ПОСЛЕДНЕЕ изменение файла; полная история — цепочка версий файла."""
    out = []
    if not raw or b"diff_vals" not in raw:
        return out
    for m in re.finditer(rb"diff_vals", raw):
        seg = raw[m.end():m.end() + 300]
        kd, kn, ko = seg.find(b"dim_name"), seg.find(b"new_val"), seg.find(b"old_val")
        if kd < 0 or kn < 0:
            continue
        nm = _dim_name(seg, kd)
        if not nm:
            continue
        new = _hist_val(seg[kn + 7:kd] if kn < kd else b"")
        old = _hist_val(seg[ko + 7:kn] if 0 <= ko < kn else b"")
        if new is None:
            continue
        out.append({"name": nm, "old": old, "new": new})
        if len(out) >= 200:
            break
    return out
def parent_file(nm, is_part):
    """Имя файла родителя (с расширением): base -> base.prt / base.asm."""
    nm = (nm or "").strip()
    if not nm:
        return ""
    if nm.lower().endswith((".prt", ".asm", ".drw")):
        return nm
    return nm + (".prt" if is_part else ".asm")
def provenance(raw, is_part):
    """Роль изделия и родитель (заготовка / отражение / наследование)."""
    if b"MERGE_BASE_PART" in raw:
        m = re.search(rb"MERGE_BASE_PART.{0,80}?([A-Za-z0-9_\-]{5,40})\x00", raw, re.S)
        return "наследование", parent_file(m.group(1).decode("latin-1") if m else "", True)
    if is_part:
        for m in re.finditer(rb"ref_part_tab\x00", raw):
            nm = re.search(rb"name\x00([A-Za-z0-9_\-\.]{4,47})\x00", raw[m.end():m.end() + 200])
            if nm:
                return "производная", parent_file(nm.group(1).decode("latin-1"), True)
    return "", ""
def clean_computer(text):
    """Имя компьютера из служебной строки записи.
    Пример: "Наименование компьютера: 'frezer-4'" -> "frezer-4"."""
    m = re.search(r"'([^']+)'", text or "")
    if m:
        return m.group(1).strip()
    return (text or "").strip().split(":")[-1].strip().strip("'")
def parse_changes(raw):
    """ЧТО МЕНЯЛОСЬ в модели (из внутренних записей изменения Creo).

    Возвращает {ревизия: {"dims": [...], "params": [...]}}: изменение привязано к ближайшей
    предшествующей записи истории (маркер `f7 ?? e3 <rev> 00 00`).
    Размеры — `typed_data(MTTyped_ModifyData)` -> имена `d*`; параметры — `chg_param_arr`/`param_typed_data`.
    ВАЖНО: числовые «было→стало» по размеру Creo в записи НЕ хранит (old_val/new_val пусты) —
    видно ИМЯ изменённого размера, а не значения.
    """
    marks = [(m.start(), m.group(2).decode()) for m in
             re.finditer(rb"\xf7(.)\xe3([0-9]{1,7})\x00\x00", raw)]

    def rev_at(off):
        prev = [r for r in marks if r[0] < off]
        return prev[-1][1] if prev else ""

    out = {}

    def add(rev, key, val):
        if not val:
            return
        d = out.setdefault(rev, {"dims": [], "params": []})
        if val not in d[key]:
            d[key].append(val)

    for m in re.finditer(rb"MTTyped_ModifyData", raw):
        seg = raw[m.start():m.start() + 600]
        for d in re.findall(rb"(?<![A-Za-z0-9_])(d[0-9]{1,6})(?![A-Za-z0-9_])", seg):
            add(rev_at(m.start()), "dims", d.decode("latin-1"))
    for m in re.finditer(rb"chg_param_arr", raw):
        seg = raw[m.start():m.start() + 400]
        n = re.search(rb"name\x00([^\x00]{1,40})\x00", seg)
        if n:
            add(rev_at(m.start()), "params", n.group(1).decode("utf-8", "replace"))
    for m in re.finditer(rb"param_typed_data", raw):
        seg = raw[m.start() + 16:m.start() + 160]
        t = re.search(rb"((?:\xd0[\x80-\xbf]|\xd1[\x80-\xbf])[^\x00]{1,40})\x00", seg)
        if t:
            try:
                add(rev_at(m.start()), "params", t.group(1).decode("utf-8"))
            except UnicodeDecodeError:
                pass
    return out
def changes_line(chg):
    """Короткая строка «что изменено» из словаря изменений одной записи."""
    if not chg:
        return ""
    parts = []
    if chg.get("dims"):
        parts.append("размеры: " + ", ".join(chg["dims"]))
    if chg.get("params"):
        parts.append("параметры: " + ", ".join(chg["params"]))
    return "; ".join(parts)
def sibling_versions(path):
    """Все версии того же изделия в папке: [(номер, путь), ...] по возрастанию."""
    folder = os.path.dirname(path)
    m = re.match(r"^(.*)\.([A-Za-z_]{2,4})\.(\d+)$", os.path.basename(path))
    if not m:
        return []
    stem, ext = m.group(1).lower(), m.group(2).lower()
    out = []
    try:
        for n in os.listdir(folder):
            mm = re.match(r"^(.*)\.([A-Za-z_]{2,4})\.(\d+)$", n)
            if mm and mm.group(1).lower() == stem and mm.group(2).lower() == ext:
                out.append((int(mm.group(3)), os.path.join(folder, n)))
    except OSError:
        return []
    out.sort()
    return out
def kind(raw):
    head = raw[:40].decode("cp1251", "replace")
    m = re.match(r"#UGC:2\s+([A-Z_/]+)", head)
    return m.group(1) if m else "?"
