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
STAMP2 = re.compile(rb"\xe1\xf6\xe1([\x20-\x7e\xc0-\xff]{1,24}?)\x00\xe2(.)(.)(.)(.)(.)(.)", re.S)
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
    """Параметры изделия `<имя>\\0 e2 33 <текст>`: сначала секция NeuPrtSld, затем — по ВСЕМУ файлу
    (у .asm/.prt часть параметров лежит вне этой секции: МАТЕРИАЛ, PTC_MATERIAL_NAME, НАИМЕНОВАНИЕ…)."""
    out = {}
    off, ln = toc.get("NeuPrtSld", (0, 0))
    for src in (raw[off:off + ln], raw):
        for m in re.finditer(
                rb"([\x20-\xff]{3,32})\x00(?:\xe2\x33|\x27\x88\x20\xe3\x33)(.{0,80}?)\x00", src, re.S):
            t = re.search(r"[\w]+$", m.group(1).decode("utf-8", "replace"))
            try:
                v = m.group(2).decode("utf-8")
            except UnicodeDecodeError:
                continue
            if t and v and "\x00" not in v:
                out.setdefault(t.group(0), " ".join(v.split()))
    return out


VAL_TAGS = (b"\xe2\x33", b"\x27\x88\x20\xe3\x33")   # значение параметра | значение отношения


def param(raw, names, default=""):
    """Значение параметра по списку имён — ищем по ВСЕМУ файлу, в UTF-8 и cp1251, по всем тегам значения.
    Параметр может быть задан и вручную, и уравнением — берём первое найденное НЕПУСТОЕ значение."""
    for nm in names:
        if not nm:
            continue
        for enc in ("utf-8", "cp1251"):
            try:
                nb = nm.encode(enc)
            except Exception:
                continue
            pos = 0
            while True:
                i = raw.find(nb, pos)
                if i < 0:
                    break
                pos = i + 1
                h = raw[i + len(nb): i + len(nb) + 12]
                for tag in VAL_TAGS:
                    if h.startswith(b"\x00" + tag):
                        v = raw[i + len(nb) + 1 + len(tag):]
                        j = v.find(b"\x00")
                        if j < 0:
                            j = 48
                        v = v[:j]
                        try:
                            s = v.decode("utf-8")
                        except UnicodeDecodeError:
                            try:
                                s = v.decode("cp1251")
                            except Exception:
                                continue
                        s = " ".join(s.split())
                        if s and "\x00" not in s:
                            return s
    return default


def compose(raw, rule):
    """Собрать значение по ПРАВИЛУ-шаблону:
      `{ИМЯ}`  — значение параметра;  `"текст"` — литерал (КАВЫЧКИ НЕ ВЫВОДЯТСЯ);
      `+` и пробелы между частями — только склейка (в значение не попадают).
    Пустые параметры отбрасываются, лишние пробелы сжимаются.
    Правило без `{` и `"` — просто имя параметра.
    """
    rule = rule or ""
    if "{" not in rule and '"' not in rule:
        return param(raw, [rule.strip()])
    out, i, n = [], 0, len(rule)
    while i < n:
        c = rule[i]
        if c == "{":
            j = rule.find("}", i)
            if j < 0:
                break
            v = param(raw, [rule[i + 1:j].strip()])
            if v:
                out.append(v)
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
            out.append(" ")                    # пробел в правиле = пробел в выводе
            i += 1
        else:
            j = i
            while j < n and rule[j] not in '{+"':
                j += 1
            out.append(rule[i:j])
            i = j
    return " ".join("".join(out).split())


def role(raw, stems=frozenset(), me=""):
    """Роль изделия по правилам §8.5 (имя файла НЕ признак):
    `MFG` — сборка `ASSEM_MFG`; `nasled.<база>` — `MERGE_BASE_PART` (отражение/отливка);
    `proizv.<родитель>` — `ref_part_tab.name` из ТОЙ ЖЕ папки (у обычной детали там шаблонный
    `MM_ASSY`/`SBORKA_MM` — не роль, поэтому сверяем с именами папки)."""
    if b"ASSEM_MFG" in raw[:400]:
        return "MFG"
    if b"MERGE_BASE_PART" in raw:
        m = re.search(rb"MERGE_BASE_PART.{0,80}?([A-Za-z0-9_\-]{5,40})\x00", raw, re.S)
        base = m.group(1).decode("latin-1") if m else ""
        if base and base.upper() not in ("MM_ASSY", "MM_PART"):
            return "nasled." + base
    for m in re.finditer(rb"ref_part_tab\x00", raw):
        nm = re.search(rb"name\x00([A-Za-z0-9_\-\.]{4,47})\x00", raw[m.end():m.end() + 200])
        if nm:
            s = stem(nm.group(1).decode("latin-1"))
            if s != me and (not stems or s in stems):
                return "proizv." + nm.group(1).decode("latin-1")
    return ""


def user_time(raw):
    """Все пары (позиция, пользователь, дата) из истории — по возрастанию позиции.
    Две раскладки записи: `f7 14 <user> 00 e2 <6 байт>` и `e1 f6 e1 <user> 00 e2 <6 байт>`."""
    out = []
    for rx in (STAMP, STAMP2):
        for m in rx.finditer(raw):
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
            "rev": h[0], "author": h[1], "revdate": h[2],
            "role": role(raw, stems, stem(os.path.basename(path))), "refs": refs}
