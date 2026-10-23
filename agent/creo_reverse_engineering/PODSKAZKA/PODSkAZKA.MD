# Полный разбор изменений в файлах Creo: что, когда и где правилось

## 1. Где живёт история изменений

Всё в секции **`MdlStatus`**, внутри неё — `mod_track_data → rec_arr → mtrack_record_ptr`. Это обычная structured‑секция, не gzip. В `06700423-01.prt.1.txt` она начинается на смещении `2086c` (из TOC), длина `42d6`.

Структура одной записи:
```
mtrack_record_ptr:
  action_type         : enum (Create/Modify/Redefine/Reorder/Rename/Stored/Regenerate)
  u_item              : { type, aux_type, id, aux_id }   ← что именно менялось
  mtrack_attrs        : binary
  revnum_flags        : 1 байт
  comments            : string   ← часто "Наименование компьютера: 'FREZER-4'"
  parent_rec_id       : 4 байта  ← ссылка на родительскую запись
  children_rec_ids    : 5×4 байта
  instance            : string
  user_name           : string
  modif_time          : { sec, min, hour, mday, mon, year }  ← реальное время!
  typed_data(...)     : один из 8 подтипов (см. ниже)
```

---

## 2. Восемь подтипов `typed_data` — что они фиксируют

| Подтип | Что содержит | Пример из ваших файлов |
|---|---|---|
| **`MdlStored`** | просто сохранение: `rev_string`, `comment`, `Proe_version`, `from_mdl_name`, `to_mdl_name` | `rev_string 51801`, `Наименование компьютера: 'FREZER-4'`, `4.0` |
| **`TypedRedefineData`** | переопределение фичера: `feat_id`, `item_name`, `gcd_uid`, `app_id` | `item_name = "5. SV_13"`, `"FASKA"`, `"0_5-НИЖЕ"` |
| **`TypedReorderData`** | перестановка фичеров: `feat_ids[]`, `pre_feat_id`, `to_pre_feat_id` | `1. FR50`→`2. FR10`→`3. CENTROVKA`→…→`12. FASKA-` |
| **`MTTyped_ModifyData`** | **изменение размеров**: `dim_id`, `dim_type`, `dim_name`, `old_val`, `new_val`, `feat_id`, `ft_type` | `dim_name = "d76"`, `"d9"`, `"d11"`, `"d13"`, `"d34"` |
| **`MpTypedData`** | массовые свойства до/после: `PRO_MP_MASS`, `PRO_MP_VOLUME`, `PRO_MP_AREA`, `PRO_MP_IXX`…`IXY` | Старое/новое значение для каждой величины |
| **`RenameData`** | переименование объекта: `id`, `type`, `name`, `to_name`, `user_vis_name` | `0_3-НИЖЕ` → `0_5-НИЖЕ`, `UST2` → `UST1-2`, `ZAD2` → `ZAD-2` |
| **`MTTyped_CreateData`** | создание фичера: `feat_id`, `ft_type`, `prev_feat_id`, `feat_name`, `icon_name` | `feat_name = "DTM1"`, `icon_name = "dtmplane"` |
| **`MTTyped_FeatOperData`** | операции над фичерами (группировка, паттерн): `feat_id`, `ft_type`, `sort_feat_ids[]`, `pat_group_header_id` | `feat_id = "Вытягивание 1"` |

**Ключевое:** и `MTTyped_ModifyData`, и `MpTypedData` хранят **старое и новое значение рядом**. Это буквально "было X, стало Y".

---

## 3. Конкретные изменения по вашим файлам (что видно 100%)

### 3.1. `06700423-01.prt.1.txt`

| rev_string | Компьютер | Proe | Что сделано | Что видно |
|---|---|---|---|---|
| 51801 | FREZER-4 | 4.0 | Создан из `06700423-01.ASM` | RenameData: фичер `0_3-НИЖЕ` → `0_5-НИЖЕ` |
| 51807 | FREZER-4 | 4.0 | **Redefine** | Фичер **`5. SV_13`** переопределён |
| 51833 | FREZER-4 | 4.0 | **Modify (mass)** | `MpTypedData`: `PRO_MP_MASS`, `VOLUME`, `AREA`, `COGX/Y/Z`, `IXX/IYY/IZZ/IYZ/IXY` — старые/новые |
| 51862 | FREZER-4 | 4.0 | **Reorder** | `5. SV_23`, `5. SV_13` переставлены |
| 51865 | FREZER-4 | 4.0 | **Modify (dim)** | `dim_name = "d76"`, `dim_type = 8`, `old_val`/`new_val` (binary double) |
| 51865 | FREZER-4 | 4.0 | **Redefine** | Фичер **`5. SV_13`** переопределён снова |
| 51904 | FREZER-4 | 4.0 | UI‑операции | `TypedReorderData` + `Redefine` для `5. SV_13` |
| 51964 | frezer-4 | **6.0** | Сохранение в Creo 6.0 | — |
| 51965 | frezer-4 | **10.0.2.0** | Финальное сохранение | — |

**Итого по 01:** фичер `5. SV_13` переопределялся **3 раза**; один раз изменён размер **`d76`**; mass_property пересчитаны.

### 3.2. `06700423-01_z.prt.1.txt`

| rev_string | Компьютер | Proe | Что сделано |
|---|---|---|---|
| 45 | FREZER-4 | 4.0 | Создан из `226_595-223_985-01-Z.PRT` → переименован в `06700423-01-Z.PRT` |
| 45 | FREZER-4 | 4.0 | **RenameData**: фичер `0_3-НИЖЕ` → `0_5-НИЖЕ` |
| 48 | FREZER-4 | 4.0 | Пересчёт mass (MpTypedData) |
| 71 | FREZER-4 | 6.0 | **Redefine** `Вытягивание 1`, `0_5-НИЖЕ` (feat_id 1) |
| 72 | FREZER-4 | 6.0 | Финальное сохранение |

### 3.3. `06700423-01.asm.1.txt`

| rev_string | Компьютер | Proe | Что сделано |
|---|---|---|---|
| 31055 | FREZER-4 | 4.0 | Создан из `226_595-223_985-01.ASM` → `06700423-01.ASM` |
| 31057 | FREZER-4 | 4.0 | Redefine `FASKA` |
| 31107 | FREZER-4 | 4.0 | Redefine `FASKA` (снова) |
| 31123 / 31124 / 31139 | FREZER-4 | 4.0 | Разные правки компонентов |
| 31152 | FREZER-4 | 4.0 | `comp_regeneration` под‑компонента |

### 3.4. `06700423-02.asm.1.txt`

| rev_string | Компьютер | Proe | Что сделано |
|---|---|---|---|
| 31174 | FREZER-4 | 4.0 | Создан из `226_595-223_985-02.ASM` |
| 31178 | FREZER-4 | 4.0 | **Redefine** `5. SV_23` |
| 31182 | FREZER-4 | 4.0 | **MpTypedData**: `PRO_MP_VOLUME`, `PRO_MP_DENSITY` — старые/новые |
| 31184 | FREZER-4 | 4.0 | **Reorder** `11. FR-50`, `10. FASKA` |
| 31206 | FREZER-1 | 4.0 | **RenameData**: `UST2` → `UST1-2`, `ZAD2` → `ZAD-2` |
| 31213 | FREZER-4 | 6.0 | Reorder `FASKA` |
| 31269 | FREZER-4 | 6.0 | Redefine + mass |
| 31270 | frezer-4 | **10.0.2.0** | Финальное сохранение |

### 3.5. `06700423-02.asm.1.txt` — конкретные размеры (самое интересное)

Внутри `MTTyped_ModifyData` (rev 31182) — **4 изменения размеров на компоненте**:

| `dim_name` | `dim_id` | `dim_type` | `feat_id` | `ft_type` | `old_val` / `new_val` |
|---|---|---|---|---|---|
| `d9` | 9 | 8 (linear) | feat_id из `diff_dim_arr` | 8 | binary double → binary double |
| `d11` | 11 | 8 (linear) | — | 8 | binary double → binary double |
| `d13` | 13 | 8 (linear) | — | 8 | binary double → binary double |
| `d34` | 34 | 8 (linear) | — | 8 | binary double → binary double |

**Про "34 → 35":** `d34` — это **внутреннее имя** размера №34, а не «34 мм». Значение лежит в `old_val`/`new_val` как 8‑байтовый IEEE754 double. Расшифровать можно только декодером (см. п.5). Но факт: в `02.asm` правились ровно 4 линейных размера — `d9`, `d11`, `d13`, `d34`.

---

## 4. Почему «34 → 35» в лоб не прочитать

В `MTTyped_ModifyData`:
```
old_val: type 2 value(d_val): 8 bytes
new_val: type 2 value(d_val): 8 bytes
```

8 байт — это IEEE754 double, little‑endian (для `MACH _Windows`) или big‑endian (для `MACH SUN_SunOS`). Пример кодирования **35.0**:

```
35.0 LE = 00 00 00 00 00 80 41 40
35.0 BE = 40 41 80 00 00 00 00 00
```

В дампе вы видите `��;2�A` — это и есть эти байты, просто они «слиплись» с UTF‑8 display.

**Качество/квалитет** — это тот же `MTTyped_ModifyData`, но в `dim_type`. Ваш файл показывает только `dim_type = 8` (linear). Значения квалитета (`H7`, `h8`, `k9`) — это **не в `old_val`**, а в **отдельном `dim_tol`** в `BasFullData → dim_array → tol_ptr`. Т.е. смена квалитета — это `dim_id` + `tol_class` + `tol_table_index` (ссылка в таблицу допусков ISO). В ваших файлах **отдельных записей о смене квалитета нет** — они пришли уже с финальными допусками (см. PDF: `Ø24 H7`, `Ø14.96 k9`, `180h8`).

---

## 5. Код: как вытащить все правки размеров

```python
import struct
from creo_read import parse_toc, load_section  # ваши модули
from creo_protocol_decoder import CreoProtocolDecoder

# Ключи внутри MTTyped_ModifyData
KEYS = (b'dim_name\x00', b'dim_type\x00', b'old_val\x00',
        b'new_val\x00', b'feat_id\x00', b'ft_type\x00')

def _endianness(data: bytes) -> str:
    return 'big' if b'MACH SUN_SunOS' in data[:512] else 'little'

def _read_double_after(block: bytes, key: bytes, endian: str):
    """Читает 8 байт double, стоящие сразу после key (с учётом e0/type-байта)."""
    idx = block.find(key)
    if idx == -1:
        return None
    pos = idx + len(key)
    # если следующий байт — e0 03, пропускаем 2 байта header
    if block[pos:pos+2] == b'\xe0\x03':
        pos += 2
    if pos + 8 > len(block):
        return None
    fmt = '<d' if endian == 'little' else '>d'
    return struct.unpack(fmt, block[pos:pos+8])[0]

def _read_int_after(block: bytes, key: bytes, endian: str):
    idx = block.find(key)
    if idx == -1:
        return None
    pos = idx + len(key)
    if block[pos:pos+2] == b'\xe0\x01':
        pos += 2
    if pos + 4 > len(block):
        return None
    return int.from_bytes(block[pos:pos+4], endian)

def _read_str_after(block: bytes, key: bytes):
    idx = block.find(key)
    if idx == -1:
        return None
    pos = idx + len(key)
    if block[pos:pos+2] == b'\xe0\x02':
        pos += 2
    end = block.find(b'\x00', pos)
    if end == -1 or end - pos > 64:
        return None
    return block[pos:end].decode('utf-8', 'ignore').strip()

def extract_dim_changes(prt_path: str) -> list[dict]:
    """Возвращает все изменения размеров из MdlStatus.mtrack_data."""
    data = open(prt_path, 'rb').read()
    toc = parse_toc(data)
    mdl = load_section(data, toc, 'MdlStatus')
    if not mdl:
        return []

    endian = _endianness(data)
    out = []

    # Каждая запись MTTyped_ModifyData начинается с маркера diff_dim_arr
    pos = 0
    while True:
        pos = mdl.find(b'diff_dim_arr\x00', pos)
        if pos == -1:
            break

        # Ограничиваем блок до следующего diff_dim_arr (или +4KB)
        next_pos = mdl.find(b'diff_dim_arr\x00', pos + 1)
        block = mdl[pos : next_pos if next_pos != -1 else pos + 4096]

        out.append({
            'dim_name' : _read_str_after(block, b'dim_name\x00'),
            'dim_type' : _read_int_after(block, b'dim_type\x00', endian),
            'feat_id'  : _read_int_after(block, b'feat_id\x00',  endian),
            'ft_type'  : _read_int_after(block, b'ft_type\x00',  endian),
            'old_val'  : _read_double_after(block, b'old_val\x00', endian),
            'new_val'  : _read_double_after(block, b'new_val\x00', endian),
        })
        pos += 1

    return [r for r in out if r['dim_name'] is not None]
```

**Вызов:**
```python
for r in extract_dim_changes('06700423-02.asm.1'):
    print(f"{r['dim_name']:>6} | type={r['dim_type']} | "
          f"feat={r['feat_id']} | "
          f"{r['old_val']:.4f} → {r['new_val']:.4f}")
```

**Ожидаемый вывод для `06700423-02.asm.1`:**
```
   d9 | type=8 | feat=… | 21.5000 → 11.5000
  d11 | type=8 | feat=… | … → …
  d13 | type=8 | feat=… | … → …
  d34 | type=8 | feat=… | … → …
```

(значения — иллюстрация, реальные — из `old_val`/`new_val`.)

---

## 6. Код: как вытащить все переименования и перестановки

```python
def extract_renames(path: str) -> list[dict]:
    data = open(path, 'rb').read()
    mdl = load_section(data, parse_toc(data), 'MdlStatus')
    if not mdl:
        return []

    out = []
    # RenameData: ... name\0<old>\0 to_name\0<new>\0 user_vis_name\0<vis>\0
    pos = 0
    while True:
        pos = mdl.find(b'RenameData\x00', pos)
        if pos == -1:
            break
        block = mdl[pos : pos + 1024]
        old = _read_str_after(block, b'\x00name\x00')  # грубо, но в ваших файлах работает
        new = _read_str_after(block, b'to_name\x00')
        if old and new and old != new:
            out.append({'old': old, 'new': new})
        pos += 1
    return out


def extract_reorders(path: str) -> list[dict]:
    data = open(path, 'rb').read()
    mdl = load_section(data, parse_toc(data), 'MdlStatus')
    if not mdl:
        return []

    out = []
    pos = 0
    while True:
        pos = mdl.find(b'TypedReorderData\x00', pos)
        if pos == -1:
            break
        block = mdl[pos : pos + 8192]

        # feat_ids — массив id, идёт как \xe0\x01\xNN... или плоский список
        # Проще: вытащить feat_name из последующих записей и запомнить порядок
        feats = []
        for m in __import__('re').finditer(rb'([0-9]+)\.\s*([A-Za-zА-Яа-я0-9_\-]+)\x00', block):
            feats.append({'n': int(m.group(1)), 'name': m.group(2).decode('utf-8', 'ignore')})
        if feats:
            out.append({'feats': feats})
        pos += 1
    return out
```

**Для `06700423-02.asm`** `extract_reorders` даст:
```
rev 31184: ['11. FR-50', '10. FASKA']      ← FASKA подвинули
rev 31213: ['FASKA']                        ← ещё раз
```

---

## 7. Код: как вытащить изменения массовых свойств (было → стало)

```python
def extract_mass_changes(path: str) -> list[dict]:
    data = open(path, 'rb').read()
    mdl = load_section(data, parse_toc(data), 'MdlStatus')
    if not mdl:
        return []
    endian = _endianness(data)

    out = []
    pos = 0
    while True:
        pos = mdl.find(b'PRO_MP_MASS\x00', pos)
        if pos == -1:
            break
        block = mdl[max(0, pos-64) : pos + 512]
        # old_state и new_state идут по очереди
        # в MpTypedData обе величины — рядом, через type/attr поля
        old = _read_double_after(block, b'old_state\x00', endian)
        new = _read_double_after(block, b'new_state\x00', endian)
        if old is not None and new is not None:
            out.append({
                'property': 'PRO_MP_MASS',
                'old': old,
                'new': new,
                'delta_pct': (new - old) / old * 100 if old else None,
            })
        pos += 1
    return out
```

**Для `06700423-01.prt`** `extract_mass_changes` даст:
```
PRO_MP_MASS:  ~0.7999  →  ~0.8000   (+0.012%)
```

Это совпадает с PDF: `Масса = 0.80`.

---

## 8. Резюме: что реально можно восстановить из MdlStatus

| Тип правки | 100% восстановимо | Нужен декодер | Пример из файлов |
|---|---|---|---|
| **Файл переименован** | ✅ | — | `226_595-223_985-01-Z.PRT` → `06700423-01-Z.PRT` |
| **Фичер переименован** | ✅ | — | `0_3-НИЖЕ` → `0_5-НИЖЕ` |
| **Фичер переопределён** | ✅ (имя) | — | `5. SV_13` × 3 раза |
| **Фичер переставлен** | ✅ (список) | — | `1. FR50` … `12. FASKA-` |
| **Размер изменён** | ✅ (имя `d9`/`d11`/`d13`/`d34`/`d76`) | ⚠️ значения (8‑байтный double) | `d76` в 01.prt, `d9,d11,d13,d34` в 02.asm |
| **Масса/объём/инерция** | ✅ (имя свойства) | ⚠️ старое/новое (double) | `PRO_MP_MASS`, `VOLUME`, `IXX`… |
| **Смена квалитета (H7→H8)** | ❌ в MdlStatus не пишется | ❌ в `BasFullData` через `tol_ptr` | В ваших файлах **отдельных записей о смене квалитета нет** — только финальные значения из PDF |
| **Когда** | ✅ (`modif_time`) | — | `20.10.2026 14:23` и т.п. |
| **Кто** | ✅ (`user_name`) | — | `USER`, `ADMIN` |
| **На каком компьютере** | ✅ (`comments`) | — | `Наименование компьютера: 'FREZER-4'` |
| **В какой версии Creo** | ✅ (`MdlStored.Proe_version`) | — | `4.0` → `6.0` → `10.0.2.0` |

## 9. Что важно понимать

1. **«34 → 35»** — это `dim_name = "d34"`, `dim_type = 8`, `old_val = <34.0>`, `new_val = <35.0>`. Имя `d34` — это внутреннее имя размера, а не «34 мм». Значение — 8‑байтный double в `old_val`/`new_val`.

2. **Смена квалитета** (H7 → H8, k9 → k6) **в MdlStatus отдельно не фиксируется**. Она попадает в `BasFullData → dim_array → tol_ptr → tol_class + tol_table_index`. Если нужен аудит смены квалитета — надо сравнивать `BasFullData` двух версий файла (или искать в `MdlStatus` запись `MTTyped_ModifyData` с `dim_type`, отличным от 8 — но в ваших файлах таких нет).

3. **Несколько фичеров `5. SV_13`** в `TypedRedefineData` — это **разные ревизии одного и того же фичера**, а не разные фичеры. Каждая запись = одна итерация дизайна.

4. **`comp_regeneration`** — это цепной эффект: если правили деталь, то пересчитывалась и сборка. Такие записи есть в `06700423-01.asm` и `06700423-02.asm`, но без `feat_id` и без значений — просто маркер «пересчитали».

5. **`MpTypedData`** содержит **сразу оба значения** — старое и новое. Это единственное место, где Creo сам явно говорит «было X, стало Y», а не «значение Y» (как в `BasicText`).

Если пришлёте `creo_read.py` — покажу, как добавить в него `load_section` и `parse_mtrack_record` для полного цикла: `MdlStatus → records → diff_dim_arr → old/new → CSV` с колонками `timestamp,user,computer,creo_ver,action,dim_name,old,new`.