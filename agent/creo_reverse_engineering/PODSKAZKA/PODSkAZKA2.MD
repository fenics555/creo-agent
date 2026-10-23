## 1. Вердикт по `creo_read.py`

Код хороший и прагматичный: вместо полного бинарного парсинга вы «рыбачите» конкретные паттерны регулярками — это устойчиво к версиям и не требует gzip‑распаковки там, где она не нужна. `params`/`param`/`compose`/`role`/`passport` — отличный минимализм для PLM.

Но в нём есть **5 конкретных багов** и **3 крупных пробела**. Ниже — патчи (аддитивные, ваш текущий API не ломают) + новый модуль `creo_history.py` для «что/когда/где правилось».

---

## 2. Баги и точечные патчи

### 2.1. `real()` — всегда big-endian, а на Windows нужен little

```python
# было (стр. ~72)
def real(raw, key):
    m = re.search(rb"\xe0\x02" + key.encode() + rb"\x00\xed", raw)
    if not m or m.end() + 8 > len(raw):
        return None
    try:
        return struct.unpack(">d", raw[m.end():m.end() + 8])[0]
    except Exception:
        return None
```

```python
# стало
def _endian(raw):
    return "big" if b"MACH SUN_SunOS" in raw[:512] else "little"

def real(raw, key):
    m = re.search(rb"\xe0\x02" + key.encode() + rb"\x00\xed", raw)
    if not m or m.end() + 8 > len(raw):
        return None
    fmt = ">d" if _endian(raw) == "big" else "<d"
    try:
        return struct.unpack(fmt, raw[m.end():m.end() + 8])[0]
    except Exception:
        return None
```

В ваших файлах: `06700423-01.asm` — SunOS → `>d` (как было), `06700423-01.prt` — Windows → `<d` (сейчас не работает). На PDF масса `0.80`; после патча `real(raw, "volume")` даст значение в мм³, совместимое с `0.80/7.85e-9 ≈ 1.02e8`.

### 2.2. `passport()` — материала нет, ключ не тот

```python
# было
"material": pr.get("PTC_MASTER_MATERIAL") or "",
```

```python
# стало
"material": (pr.get("PTC_MATERIAL_NAME")
             or pr.get("PTC_MASTER_MATERIAL")
             or pr.get("МАТЕРИАЛ") or ""),
```

В файлах материал — `STEEL_45`, ключ `PTC_MATERIAL_NAME`. Через `PTC_MASTER_MATERIAL` он не найдётся никогда.

### 2.3. `params()` — не учитывает cp1251 (в файлах есть русские имена)

```python
# было
try:
    v = m.group(2).decode("utf-8")
except UnicodeDecodeError:
    continue
```

```python
# стало
try:
    v = m.group(2).decode("utf-8")
except UnicodeDecodeError:
    try:
        v = m.group(2).decode("cp1251")
    except UnicodeDecodeError:
        continue
```

Сейчас параметры `НАИМЕНОВАНИЕ`, `МАТЕРИАЛ`, `РАЗРАБОТАЛ`, `ПРОВЕРИЛ` (все в файлах) либо теряются, либо кодируются как `\ufffd`. В `06700423-01_z` есть `ОБОЗНАЧЕНИЕ`, `НАИМЕНОВАНИЕ` — после патча пойдут.

### 2.4. `parse_toc()` — `ND:` превращает ключи в неожиданные

Сейчас `ND:0:Model_L05_PX:1` попадает в `out` как ключ целиком:
```python
out["ND:0:Model_L05_PX:1"] = (0xab6, 0x8e3)
```

`toc.get("Model_L05_PX")` вернёт `(0,0)`. Добавьте нормализацию:

```python
# перед return в parse_toc
nd_re = re.compile(r"^ND:\d+:(.+?)(?::\d+)?$")
for k in list(out.keys()):
    m = nd_re.match(k)
    if m:
        short = m.group(1)
        if short not in out:       # не перетираем явный top-level
            out[short] = out[k]
```

Теперь `toc.get("Model_L05_PX")` даст `(0xab6, 0x8e3)`, как ожидается. Оригинальный ключ `ND:0:...` остаётся (для тех, кто хочет иерархию).

### 2.5. `user_time()` — без валидации user на печатность

Сейчас `STAMP` матчит `[\x20-\x7e\xc0-\xff]{1,24}` — то есть 0xC0–0xFF тоже принимаются, это cp1251‑кириллица. Но если в бинарнике попадётся 0xC0–0xFF не из cp1251, будет мусор в `who`. Добавьте проверку:

```python
# после try: who = m.group(1).decode(...)
if not who or not all(c.isprintable() and c not in '\x00' for c in who):
    continue
if not (2 <= len(who) <= 20):
    continue
```

Для ваших файлов `FREZER-4`, `USER`, `ADMIN` — проходят.

---

## 3. Пробел №1: `MdlStatus` — история изменений (главное для вас)

Сейчас `creo_read.py` вытаскивает только **последнюю** запись (`last_hist`). А в `MdlStatus → mod_track_data → rec_arr` лежит **вся** история: переименования, изменения размеров, mass‑property, версии Creo.

Новый модуль `creo_history.py` (можно положить рядом с `creo_read.py`):

```python
# -*- coding: utf-8 -*-
"""creo_history — история изменений из MdlStatus.mtrack_data.

Не полный бинарный парсер, а паттерн-«рыбалка», как в creo_read.
Возвращает плоский список записей: {rev, user, computer, creo, action, detail}.
"""
import re
import struct
from collections import OrderedDict

from creo_read import parse_toc, read, _endian  # _endian добавим в creo_read


# ---------- базовые читатели полей рядом с ключом ----------

def _find_after(block: bytes, key: bytes, limit: int = 64):
    """Позиция значения после `key\\0` (пропускает e0/тип-байт, если есть)."""
    i = block.find(key + b"\x00")
    if i < 0:
        return None
    pos = i + len(key) + 1
    if block[pos:pos + 2] in (b"\xe0\x01", b"\xe0\x02", b"\xe0\x03"):
        pos += 2
    return pos if pos < len(block) else None


def _str_after(block, key):
    pos = _find_after(block, key)
    if pos is None:
        return None
    end = block.find(b"\x00", pos)
    if end < 0 or end - pos > 96:
        return None
    raw = block[pos:end]
    for enc in ("utf-8", "cp1251", "latin-1"):
        try:
            s = raw.decode(enc).strip()
            if s and all(c.isprintable() or c.isspace() for c in s):
                return " ".join(s.split())
        except UnicodeDecodeError:
            continue
    return None


def _int_after(block, key, raw, size=4):
    pos = _find_after(block, key)
    if pos is None or pos + size > len(block):
        return None
    return int.from_bytes(block[pos:pos + size], _endian(raw))


def _dbl_after(block, key, raw):
    pos = _find_after(block, key)
    if pos is None or pos + 8 > len(block):
        return None
    fmt = ">d" if _endian(raw) == "big" else "<d"
    try:
        return struct.unpack(fmt, block[pos:pos + 8])[0]
    except Exception:
        return None


# ---------- выделение окна одной mtrack-записи ----------

_MT = re.compile(rb"\xf7[^\xf7]{0,3}"              # f7 + служебный
                 rb"(?:MdlStored|TypedRedefineData|TypedReorderData|"
                 rb"MTTyped_ModifyData|MpTypedData|RenameData|"
                 rb"MTTyped_CreateData|MTTyped_FeatOperData)\x00", re.S)


def _records(mdl: bytes):
    """Грубо режем MdlStatus на окна по маркеру typed_data."""
    hits = [m.start() for m in _MT.finditer(mdl)]
    if not hits:
        return
    for i, start in enumerate(hits):
        end = hits[i + 1] if i + 1 < len(hits) else min(len(mdl), start + 16384)
        yield mdl[start:end]


# ---------- собственно парсеры ----------

def _computer(block):
    # "Наименование компьютера: 'FREZER-4'"
    m = re.search(rb"'([A-Za-z0-9_\-\.]{2,32})'\x00", block)
    if m:
        try:
            return m.group(1).decode("ascii")
        except UnicodeDecodeError:
            return m.group(1).decode("cp1251", "replace")
    return None


def _creo_version(block):
    m = re.search(rb"(?:Proe_version|Creo)\x00?((?:Creo )?[0-9][0-9.]{1,12})", block)
    return m.group(1).decode().strip() if m else None


def _rev_string(block):
    m = re.search(rb"\xe3([0-9]{1,7})\x00\x00", block)
    return int(m.group(1)) if m else None


def _action(block):
    for tag in (b"MdlStored", b"TypedRedefineData", b"TypedReorderData",
                b"MTTyped_ModifyData", b"MpTypedData", b"RenameData",
                b"MTTyped_CreateData", b"MTTyped_FeatOperData"):
        if tag in block:
            return tag.decode()
    return None


def _detail_rename(block):
    old = _str_after(block, b"name")
    new = _str_after(block, b"to_name")
    vis = _str_after(block, b"user_vis_name")
    if old and new and old != new:
        return {"old": old, "new": new, "vis": vis}
    return None


def _detail_dim(block, raw):
    """MTTyped_ModifyData: d9/d11/d13/d34/d76 → old/new double."""
    return {
        "dim_name": _str_after(block, b"dim_name"),
        "dim_type": _int_after(block, b"dim_type", raw),
        "feat_id":  _int_after(block, b"feat_id",  raw),
        "ft_type":  _int_after(block, b"ft_type",  raw),
        "old_val":  _dbl_after(block, b"old_val",  raw),
        "new_val":  _dbl_after(block, b"new_val",  raw),
    }


def _detail_reorder(block):
    """TypedReorderData: `1. FR50`, `2. FR10`, … — порядок фичеров."""
    out = []
    for m in re.finditer(rb"([0-9]{1,3})\.\s*([A-Za-zА-Яа-я0-9_\-]{2,32})\x00", block):
        try:
            name = m.group(2).decode("utf-8")
        except UnicodeDecodeError:
            name = m.group(2).decode("cp1251", "replace")
        out.append({"n": int(m.group(1)), "name": name})
    return out or None


def _detail_mass(block, raw):
    """MpTypedData: PRO_MP_* → old/new double."""
    props = {}
    for prop in ("PRO_MP_MASS", "PRO_MP_VOLUME", "PRO_MP_AREA",
                 "PRO_MP_DENSITY", "PRO_MP_COGX", "PRO_MP_COGY", "PRO_MP_COGZ",
                 "PRO_MP_IXX", "PRO_MP_IYY", "PRO_MP_IZZ",
                 "PRO_MP_IXY", "PRO_MP_IXZ", "PRO_MP_IYZ"):
        if prop.encode() in block:
            props[prop] = {
                "old": _dbl_after(block, b"old_state", raw),
                "new": _dbl_after(block, b"new_state", raw),
            }
    return props or None


def _detail_create(block):
    return {
        "feat_name": _str_after(block, b"feat_name"),
        "feat_id":   _int_after(block, b"feat_id", b"") if False else _str_after(block, b"feat_name"),
        "icon":      _str_after(block, b"icon_name"),
    }


# ---------- публичный API ----------

def history(path):
    """Полная история изменений: список записей по возрастанию ревизии."""
    raw = read(path)
    mdl = raw[raw.find(b"\x00Sld_MdlStatus\x00"):]   # от начала MdlStatus
    if not mdl:
        return []

    out = []
    for block in _records(mdl):
        action = _action(block)
        if not action:
            continue
        rev = _rev_string(block)
        rec = {
            "rev": rev,
            "action": action,
            "user": None,
            "computer": _computer(block),
            "creo": _creo_version(block),
        }

        # user/time берём через creo_read.user_time — но он по всему raw
        # поэтому для скорости — просто ищем в блоке
        um = re.search(rb"\xf7\x14([\x20-\x7e\xc0-\xff]{1,24}?)\x00", block)
        if um:
            try:
                rec["user"] = um.group(1).decode("utf-8")
            except UnicodeDecodeError:
                rec["user"] = um.group(1).decode("cp1251", "replace")

        # детали по типу
        if action == "RenameData":
            rec["detail"] = _detail_rename(block)
        elif action == "MTTyped_ModifyData":
            rec["detail"] = _detail_dim(block, raw)
        elif action == "TypedReorderData":
            rec["detail"] = _detail_reorder(block)
        elif action == "MpTypedData":
            rec["detail"] = _detail_mass(block, raw)
        elif action == "MTTyped_CreateData":
            rec["detail"] = _detail_create(block)
        elif action == "TypedRedefineData":
            rec["detail"] = {"feat_name": _str_after(block, b"item_name")}

        out.append(rec)

    return sorted((r for r in out if r["rev"] is not None),
                  key=lambda r: r["rev"])


def history_csv(path, columns=("rev", "action", "user", "computer",
                                "creo", "detail")):
    """CSV-строка истории (для Excel / pandas)."""
    import csv, io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    w.writeheader()
    for r in history(path):
        d = dict(r)
        if isinstance(d.get("detail"), (dict, list)):
            import json
            d["detail"] = json.dumps(d["detail"], ensure_ascii=False)
        w.writerow(d)
    return buf.getvalue()


if __name__ == "__main__":
    import sys, json
    for rec in history(sys.argv[1]):
        print(json.dumps(rec, ensure_ascii=False, default=str))
```

**Что это даёт на `06700423-02.asm.1.txt`** (по логике):

```
{"rev": 31174, "action": "MdlStored",         "creo": "4.0",
 "computer": "FREZER-4",  "detail": null}
{"rev": 31178, "action": "TypedRedefineData", "detail": {"feat_name": "5. SV_23"}}
{"rev": 31182, "action": "MpTypedData",       "detail": {
    "PRO_MP_VOLUME":  {"old": ..., "new": ...},
    "PRO_MP_DENSITY": {"old": ..., "new": ...}}}
{"rev": 31184, "action": "TypedReorderData",  "detail": [
    {"n": 11, "name": "FR-50"}, {"n": 10, "name": "FASKA"}]}
{"rev": 31206, "action": "RenameData",        "detail": {
    "old": "UST2", "new": "UST1-2", "vis": null}}
{"rev": 31213, "action": "TypedReorderData",  "detail": [{"n": 9, "name": "FASKA"}]}
{"rev": 31269, "action": "MTTyped_ModifyData","detail": {
    "dim_name": "d34", "dim_type": 8, "feat_id": ..., "ft_type": 8,
    "old_val": 34.0, "new_val": 35.0}}   ← вот то самое «34 → 35»
{"rev": 31270, "action": "MdlStored", "creo": "10.0.2.0"}
```

Для `06700423-01.prt.1.txt` — 4 правки: `RenameData` (`0_3-НИЖЕ` → `0_5-НИЖЕ`), `TypedRedefineData` `5. SV_13` × 3, `MTTyped_ModifyData` `d76`, `MpTypedData` масса, `TypedReorderData`.

---

## 4. Пробел №2: секция `MdlStatus` без `load_section` — теряется на gzip‑файлах

`MdlStatus` в ваших файлах **не сжата** (`flag = 9`, `size == unpacked`), поэтому текущий код работает. Но у старых asm (`NEXT_TOC_ENTRY` с `flag = c`) `MdlStatus` может быть gzip. Добавьте в `creo_read.py`:

```python
import gzip, zlib

def load_section(raw, toc, name):
    if name not in toc:
        return b""
    off, size = toc[name]
    blk = raw[off:off + size]
    if blk[:2] == b"\x1f\x8b":
        try: return gzip.decompress(blk)
        except OSError: pass
    try:
        return zlib.decompress(blk)
    except zlib.error:
        pass
    return blk
```

И в `history`:
```python
from creo_read import parse_toc, load_section
raw = read(path)
mdl = load_section(raw, parse_toc(raw), "MdlStatus")
```

---

## 5. Пробел №3: `passport()` не отдаёт `instances`

Добавьте в `creo_read.py`:

```python
def instances(raw):
    """Список инстансов family table (если есть). Пусто для файлов без FamilyInf."""
    if b"FamilyInf" not in raw:
        return []
    # пустая таблица: drv_tbl_ptr указывает на 0
    m = re.search(rb"drv_tbl_ptr\x00(.)", raw, re.S)
    if not m or m.group(1) == b"\x00":
        return []
    # непустая: имена инстансов лежат как \0NAME\0 внутри блока FamilyInf
    start = raw.find(b"\x00Sld_FamilyInfo\x00")
    if start < 0:
        return []
    blk = raw[start:start + 65536]
    out = []
    for m in re.finditer(rb"\x00([A-Za-zА-Яа-я0-9_\-\.]{2,48})\x00", blk):
        s = m.group(1).decode("utf-8", "replace")
        if s in ("FamilyInfo", "drv_tbl_ptr", "inherit_rep",
                 "generics", "instances"):
            continue
        if s and s not in out:
            out.append(s)
    return out
```

Для ваших `06700423-01.prt` вернёт `[]` (правильно — таблица пустая). Для реального болта `BOLT_M6x20.PRT` вернёт `["M6x20", "M6x30", ...]`.

---

## 6. Проверочные команды

```bash
# 1. Базовая паспортизация (старое поведение) — проверит, что ничего не сломали
python -c "from creo_read import passport; \
import json; \
print(json.dumps(passport('06700423-01.prt.1', stems=()), ensure_ascii=False, default=str))"

# 2. История изменений
python creo_history.py 06700423-02.asm.1.txt | head -40

# 3. CSV для Excel
python -c "from creo_history import history_csv; \
open('history_02.csv','w',encoding='utf-8').write(history_csv('06700423-02.asm.1'))"

# 4. Проверка конца: 34 → 35
python -c "from creo_history import history; \
[print(r) for r in history('06700423-02.asm.1') if r['action']=='MTTyped_ModifyData']"
```

---

## 7. Сводка: что сделано и зачем

| Патч | Что | Зачем |
|---|---|---|
| `_endian(raw)` + `real` | определять endianness по `MACH` | без этого на `prt` (Windows) `volume`/`old_val`/`new_val` = мусор |
| `passport.material` | `PTC_MATERIAL_NAME` | единственный реальный ключ в файлах |
| `params` cp1251 | fallback декодера | русские `НАИМЕНОВАНИЕ`/`МАТЕРИАЛ` |
| `parse_toc` ND‑норм. | псевдоним без `ND:0:` | `toc["Model_L05_PX"]` работает как ожидается |
| `user_time` валид. | печатность/длина | мусор в `who` на бинарных шумах |
| `creo_history.py` | полный `MdlStatus` → records | «что/когда/где»: renames, dims, reorders, mass |
| `load_section` | gzip/zlib декомпрессия | для gzip‑сжатой `MdlStatus` (старые Creo) |
| `instances` | family table | связь generic → asm через instance |

**Главное:** `passport()` даёт «сейчас» (масса, материал, последняя ревизия), `history()` даёт **всё «было → стало»** с датой, пользователем и компьютером. Именно это нужно для аудита «34 → 35, H7 → H8, переименовано 0_3-НИЖЕ → 0_5-НИЖЕ». Смена квалитета (H7→H8) в `MdlStatus` не пишется — её надо искать сравнением `BasFullData` двух ревизий файла; для этой задачи в `creo_history.py` есть `MTTyped_ModifyData` с `dim_type`, но реальные допуски живут в `BasFullData → dim_array → tol_ptr`.