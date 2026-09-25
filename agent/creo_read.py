# -*- coding: utf-8 -*-
r"""creo_read — ЕДИНЫЙ ЧИТАТЕЛЬ ФАЙЛОВ CREO «В ЛОБ» (общая библиотека дома).

Одна реализация чтения — её используют инструменты (`plm_tree`, `plm_reader`), чтобы не плодить
копии парсера. Creo не нужен, только стандартная библиотека.
"""
import datetime
import os
import re
import struct
from collections import Counter

TAIL = re.compile(rb"\xf7(.)\xe3([0-9]{1,7})\x00\x00(.{0,220}?)\x00((?:Creo )?[0-9][0-9.]*)\x00", re.S)
STAMP = re.compile(rb"\xf7\x14([\x20-\x7e\xc0-\xff]{1,24}?)\x00\xe2(.)(.)(.)(.)(.)(.)", re.S)
NAME_B = re.compile(rb"[\x00-\x1f\x80-\xff]([A-Za-z0-9][A-Za-z0-9_\-\.]{3,47}\.(?:PRT|ASM))",
                    re.IGNORECASE)


def stem(name):
    """Имя файла → код модели (верхний регистр, без версии и расширения)."""
    n = name.upper()
    for ext in (".PRT", ".ASM", ".DRW", ".NEU", ".SEC", ".M_P", ".PRT.", ".ASM."):
        if ext in n:
            n = n.split(ext)[0]
            break
    return re.sub(r"\.\d+$", "", n)


def read(path):
    with open(path, "rb") as f:
        return f.read()


def parse_toc(raw):
    """Оглавление секций файла: {имя: (offset, length)} по цепочке NEXT_TOC_ENTRY."""
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


def real(raw, key):
    """Числовое поле `e0 02 <имя> 00 ed <8 байт BE double>` (объём, масса)."""
    m = re.search(rb"\xe0\x02" + key.encode() + rb"\x00\xed", raw)
    if not m or m.end() + 8 > len(raw):
        return None
    try:
        return struct.unpack(">d", raw[m.end():m.end() + 8])[0]
    except Exception:
        return None


def params(raw, toc):
    """Параметры изделия из NeuPrtSld (`<имя>\\0 e2 33 <текст>`)."""
    out = {}
    if "NeuPrtSld" not in toc:
        return out
    off, ln = toc["NeuPrtSld"][0], toc["NeuPrtSld"][1]
    for m in re.finditer(rb"([\x20-\xff]{3,32})\x00\xe2\x33(.{0,60}?)\x00", raw[off:off + ln], re.S):
        t = re.search(r"[\w]+$", m.group(1).decode("utf-8", "replace"))
        try:
            v = m.group(2).decode("utf-8")
        except UnicodeDecodeError:
            continue
        if t and v and "\x00" not in v:
            out.setdefault(t.group(0), " ".join(v.split()))
    return out


def role(raw):
    """Роль изделия: `nasled.<родитель>` (MERGE_BASE_PART) или `proizv.<родитель>` (ref_part_tab)."""
    if b"MERGE_BASE_PART" in raw:
        m = re.search(rb"MERGE_BASE_PART.{0,80}?([A-Za-z0-9_\-]{5,40})\x00", raw, re.S)
        return "nasled." + (m.group(1).decode("latin-1") if m else "?")
    for m in re.finditer(rb"ref_part_tab\x00", raw):
        nm = re.search(rb"name\x00([A-Za-z0-9_\-\.]{4,47})\x00", raw[m.end():m.end() + 200])
        if nm:
            return "proizv." + nm.group(1).decode("latin-1")
    return ""


def user_time(raw):
    """Все пары (позиция, пользователь, дата) из истории — по убыванию позиции."""
    out = []
    for m in STAMP.finditer(raw):
        s, mi, h, d, mo, y = (b[0] for b in m.groups()[1:])
        try:
            dt = datetime.datetime(1900 + y, mo + 1, d, h, mi, s)
        except ValueError:
            continue
        if 1990 <= dt.year <= 2030:
            try:
                who = m.group(1).decode("utf-8")
            except UnicodeDecodeError:
                who = m.group(1).decode("cp1251", "replace")
            out.append((m.start(), who, dt))
    return sorted(set(out))


def last_hist(raw):
    """Последняя запись истории: (ревизия, пользователь, дата 'дд.мм.гг чч:мм')."""
    st, last = user_time(raw), None
    for t in TAIL.finditer(raw):
        prev = [s for s in st if s[0] < t.start()]
        last = (t.group(2).decode(), prev[-1][1] if prev else "",
                prev[-1][2].strftime("%d.%m.%y %H:%M") if prev else "")
    return last


def names(raw):
    """Имена моделей внутри файла (расширение срезано) и сколько раз встречаются (входимость)."""
    c = Counter()
    for m in NAME_B.finditer(raw):
        c[stem(m.group(1).decode("latin-1"))] += 1
    return c


def passport(path, stems=()):
    """Паспорт модели из файла (Creo не нужен)."""
    raw = read(path)
    pr = params(raw, parse_toc(raw))
    vol = real(raw, "volume") or real(raw, "mtrl_volume")
    nm = names(raw)
    refs = {c: nm[c] for c in nm if c != stem(os.path.basename(path)) and c in stems and len(c) >= 5}
    h = last_hist(raw) or ("", "", "")
    return {"path": path, "size": len(raw), "mtime": os.path.getmtime(path),
            "volume": vol or 0.0, "material": pr.get("PTC_MASTER_MATERIAL") or "",
            "name": pr.get("\u041d\u0410\u0418\u041c\u0415\u041d\u041e\u0412\u0410\u041d\u0418\u0415") or "",
            "designation": pr.get("\u041e\u0411\u041e\u0417\u041d\u0410\u0427\u0415\u041d\u0418\u0415") or "",
            "rev": h[0], "author": h[1], "revdate": h[2], "role": role(raw), "refs": refs}
