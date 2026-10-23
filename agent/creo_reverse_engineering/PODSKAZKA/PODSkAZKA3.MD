# Полная модель связей Creo для PLM + что ещё есть в файлах

## 1. Таксономия связей — полная карта

### 1.1. Входимость (BOM)

| Ребро | Что значит | Где в файле | Направление |
|---|---|---|---|
| `contains` | сборка → компонент | `Dwg_Models` в `.asm` + `FeatDefsCmp.comp_data.name` | ↓ вниз от сборки, ↑ вверх от детали |
| `contains_via_instance` | сборка → компонент, вставленный как instance | `FeatDefsCmp.comp_data.instance_name` | оба |
| `contains_simp_rep` | сборка → компонент в упрощённом представлении | `simpl_rep` в `comp_data` | оба |
| `contains_flexible` | гибкий компонент (пружина, шланг) | `flex_comp_data` | оба |
| `contains_envelope` | оболочка для упрощений | `envelope_data` | оба |
| `contains_pattern` | паттерн компонентов | `pattern_member_ids` | оба |
| `contains_mirror_pattern` | зеркальный паттерн | `mirror_pat_data` | оба |

### 1.2. Наследование / зеркала / пересохранение

| Ребро | Что значит | Где в файле | Направление |
|---|---|---|---|
| `inherit` | наследование (derive) | `MdlRefInfo.top_to_part_models` + `FeatRefData` + `MERGE_BASE_PART` | ↑ вверх |
| `mirror_of` | зеркальное отражение | `MERGE_BASE_PART` + суффикс `_z` / `_mir` | ↑ вверх |
| `copied_geom` | copy geom | `Merge` в `AllFeatur` | ↑ вверх |
| `merge` / `cutout` | boolean (объединение / вычитание) | `Merge` / `Cut` в `AllFeatur` | ↑ вверх |
| `published_from` | геометрия опубликована | `publish_geom` в `FeatDefs` | ↑ вверх |
| `saved_as` | Save As / пересохранение | `MdlStatus.MdlStored.from_mdl_name → to_mdl_name` | ↑ вверх |
| `replaced_by` | Replace Component | `component_replace_data` | ↑ вверх |

### 1.3. Manufacturing

| Ребро | Что значит | Где в файле | Направление |
|---|---|---|---|
| `mfg_refers_to` | mfg-сборка → деталь | `Mfg_info.ref_part_tab` | ↑ / ↓ |
| `mfg_stock_for` | заготовка → деталь | `MERGE_BASE_PART` в stock.prt + суффикс `_z` | ↑ вверх |
| `mfg_fixture_for` | приспособление → mfg-сборка | обычный component в `Mfg_info` | ↑ вверх |
| `mfg_tool_for` | инструмент → операция | `tool_array` (`T0010`, `FASKA`) | ↑ вверх |
| `mfg_machine_for` | станок → mfg-сборка | `MACH01` в `NeuAsmSld` | ↑ вверх |
| `mfg_operation_of` | операция → mfg-сборка | `Mfg_info.step_arr` | ↑ вверх |
| `mfg_cl_for` | CL-данные → операция | `cl_info_ptr` | ↑ вверх |

### 1.4. Чертежи

| Ребро | Что значит | Где | Направление |
|---|---|---|---|
| `drawing_of` | drw → prt/asm | `Dwg_Models` в `.drw` | ↑ |
| `drawing_uses_format` | drw → форматка | `format_info` | ↑ |
| `drawing_shows_instance` | drw показывает instance | `FeatDefsCmp` в drw | ↑ |
| `drawing_bom_of` | спецификация на чертеже | `FeatDefsCmp` с `type = SB_DRAWING` | ↑ |

### 1.5. Семейство (family table)

| Ребро | Что значит | Где | Направление |
|---|---|---|---|
| `instance_of` | instance → generic | `FamilyInf.drv_tbl_ptr → Sld_DrvTable` | ↑ |
| `generic_has_instance` | generic → instance | то же | ↓ |
| `used_via_instance` | asm → generic через instance | `FeatDefsCmp.comp_data.instance_name` | ↓ |

### 1.6. Внешние ссылки (xref)

| Ребро | Что значит | Где | Направление |
|---|---|---|---|
| `xref` | ссылка на внешний файл | `MdlRefInfo.p_foreign_source` | ↑ |
| `inter_part_ref` | ссылка детали внутри сборки | `FeatRefData` с `own_ref_id` | оба |
| `layout_ref` | ссылка на Layout/Notebook | `p_layout_ref` | ↑ |
| `skeleton_ref` | ссылка на скелетон | `FeatDefsCmp` с skeleton flag | ↑ |

### 1.7. Версии / ревизии

| Ребро | Что значит | Где | Направление |
|---|---|---|---|
| `revision_of` | `X.prt.2 → X.prt.1` | имя файла + `revnum` | ↑ |
| `regen_from` | регенерация из другой ревизии | `SldRegenRevInfo` | ↑ |

## 2. Единая модель графа для PLM

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Edge:
    src: str                    # имя файла (stem)
    dst: str                    # имя файла (stem)
    type: str                   # 'contains' | 'inherit' | 'mirror_of' | ...
    via_instance: Optional[str] = None   # 'M6x20' для contains_via_instance
    direction: str = "both"     # 'up' | 'down' | 'both'
    meta: dict = field(default_factory=dict)  # {'simpl_rep': 'MASTER', 'qty': 4, ...}

@dataclass
class Graph:
    nodes: dict = field(default_factory=dict)   # stem → {path, type, role}
    edges: list = field(default_factory=list)

    def add_node(self, stem, **kw):
        self.nodes.setdefault(stem, {}).update(kw)

    def add_edge(self, edge: Edge):
        self.edges.append(edge)

    def downstream(self, stem, edge_types=None, through_instances=True):
        """Кто использует stem (вниз)."""
        out = []
        for e in self.edges:
            if e.src != stem and e.dst != stem:
                continue
            if edge_types and e.type not in edge_types:
                continue
            if not through_instances and e.via_instance:
                continue
            out.append(e)
        return out

    def upstream(self, stem, edge_types=None):
        """Из чего сделано stem (вверх)."""
        return [e for e in self.edges
                if e.dst == stem and (not edge_types or e.type in edge_types)]
```

**Главное правило для PLM:** downstream/upstream строятся **не по именам файлов**, а по кортежу `(stem, instance)`. Потому что assembly `A.asm` ссылается не на `bolt.prt`, а на `bolt.prt#M6x20`.

## 3. Код: сборщик связей из файла

```python
# creo_links.py
import os, re
from creo_read import read, parse_toc, load_section, stem, _endian
from creo_history import _str_after, _int_after

# --- helpers ---
def _comp_blocks(raw):
    """Делит FeatDefsCmp / Dwg_Models на блоки одного компонента."""
    for sec in ("FeatDefsCmp", "Dwg_Models", "Dwg_Objects"):
        toc = parse_toc(raw)
        if sec in toc:
            blk = load_section(raw, toc, sec)
            # компоненты отделяются друг от друга ключом comp_data
            for m in re.finditer(rb"comp_data\x00", blk):
                start = m.start()
                end = blk.find(b"comp_data\x00", start + 1)
                if end == -1:
                    end = len(blk)
                yield blk[start:end]

# --- BOM ---
def bom(raw):
    """Возвращает [(component_stem, instance_name, parent_asm_stem), ...]."""
    out = []
    me = stem(os.path.basename(raw_path)) if False else None
    for block in _comp_blocks(raw):
        name = _str_after(block, b"name")
        inst = _str_after(block, b"instance_name")
        if name and not inst:
            # иногда instance_name прилеплен к name через #
            if "#" in name:
                name, inst = name.split("#", 1)
        if name:
            out.append({"name": stem(name), "instance": inst, "raw_name": name})
    return out

# --- upstream (inherit/xref) ---
def upstream_refs(raw):
    """MdlRefInfo + FeatRefData → upstream-связи."""
    toc = parse_toc(raw)
    blk = load_section(raw, toc, "MdlRefInfo")
    if not blk:
        return []
    out = []
    # top_to_part_models → имя родителя
    for m in re.finditer(rb"top_to_part_models\x00", blk):
        # в блоке будет name: <source>
        end = blk.find(b"top_to_ref_models\x00", m.end())
        window = blk[m.end():end if end > 0 else m.end() + 512]
        name = _str_after(window, b"name")
        if name:
            out.append({"type": "inherit", "src": stem(name)})
    # p_foreign_source → xref
    for m in re.finditer(rb"p_foreign_source\x00", blk):
        name = _str_after(blk[m.end():m.end() + 128], b"name")
        if name:
            out.append({"type": "xref", "src": stem(name)})
    return out

# --- mirror/inherit по суффиксу ---
def mirror_of(stem_name):
    """Если stem оканчивается на _z / _mir / _mirror — вернуть базу."""
    for suf in ("_mir", "_mirror", "_m", "_z"):
        if stem_name.endswith(suf) and len(stem_name) > len(suf) + 3:
            return stem_name[:-len(suf)]
    return None

# --- family table ---
def family_instances(raw):
    """Возвращает {'generic': name, 'instances': [...]} или None."""
    if b"FamilyInf" not in raw:
        return None
    m = re.search(rb"drv_tbl_ptr\x00(.)", raw, re.S)
    if not m or m.group(1) == b"\x00":
        return None
    # Непустая — искать по секции Sld_DrvTable
    toc = parse_toc(raw)
    for sec in ("Sld_DrvTable", "DrvTable"):
        if sec in toc:
            blk = load_section(raw, toc, sec)
            names = []
            for mm in re.finditer(rb"\x00([A-Za-zА-Яа-я0-9_\-\.]{2,48})\x00", blk):
                s = mm.group(1).decode("utf-8", "replace")
                if s and s not in names and not s.startswith("Sld_"):
                    names.append(s)
            return {"generic": None, "instances": names}
    return None

# --- mfg ---
def mfg_links(raw):
    """Mfg_info: ref_part_tab (заготовка/деталь) + tool_array (инструменты)."""
    toc = parse_toc(raw)
    blk = load_section(raw, toc, "FeatDefs")
    if not blk:
        blk = raw
    out = []
    # ref_part_tab → заготовка / деталь
    for m in re.finditer(rb"ref_part_tab\x00", blk):
        name = _str_after(blk[m.end():m.end() + 200], b"name")
        if name:
            base = stem(name)
            if base.endswith("_z"):
                out.append({"type": "mfg_stock_for", "src": base[:-2]})
            else:
                out.append({"type": "mfg_refers_to", "src": base})
    # tool_array → инструменты
    for m in re.finditer(rb"tool_id\x00", blk):
        tid = _str_after(blk[m.end():m.end() + 32], b"tool_id")
        if tid and tid not in [e.get("meta", {}).get("tool") for e in out]:
            out.append({"type": "mfg_tool_for", "src": tid,
                        "meta": {"tool": tid}})
    return out
```

## 4. Что ещё есть в Creo-файлах и полезно для PLM

### 4.1. Assembly configurations (simp_rep) — критично

Одна `.asm` → **много конфигураций** (MASTER, SIMP_1, SIMP_2). В каждой — свой набор компонентов. Для PLM:

```
A.asm
├── MASTER      — 15 деталей
├── SIMP_1      — 5 деталей (упрощённый)
└── SIMP_2      — 10 деталей (без крепежа)
```

**Где:** `SimpRepArray_L05` в `Model_L05_PX`, `rep_data` в `SimpRep` + `FeatDefsCmp.simpl_rep`.

**Для PLM:** BOM должен зависеть от конфигурации. Не одна BOM на сборку, а N BOM на N конфигураций.

### 4.2. Exploded states — разнесённые виды

```
SimpRep → expl_state_ref → expld_comp_ref → offset_matrix
```

**Для PLM:** если сборка в 3D имеет разнесённый вид, это состояние тоже надо хранить; оно влияет на чертежи.

### 4.3. Publication features — публикация геометрии

Один компонент публикует поверхность/кривую, другие на неё ссылаются. При rename/delete — ломается вся цепочка. **В `FeatDefs` — `publish` фичер.**

### 4.4. External references (inter-part) — самое коварное

Деталь A внутри сборки строит вырез по детали B. Связь A→B. **В `FeatRefData` — `own_ref_id`.**

**Для PLM:** при переименовании/удалении B ломается A. Нужно предупреждать.

### 4.5. Replace Component — замена компонента

`A.asm` содержал `bolt1.prt`, заменили на `bolt2.prt`. История замены — **`FeatDefsCmp.component_replace_data`** и `MdlStatus.RenameData`.

**Для PLM:** критично — это самое частое действие.

### 4.6. Flexible components — гнущиеся

Пружины, шланги. `flex_comp_data` — параметры гибкости. При изменении базовой детали — «гнутся» иначе.

### 4.7. Envelope components — оболочки

`envelope_data` — компонент-оболочка для упрощений. Используется в simp_rep.

### 4.8. Parametric relations — формулы

`MdlStatus` / `NeuPrtSld → rel_data → relset_code_tree` — параметрические зависимости:

```
МАССА = MASS / 1000
gr = if (МАССА < 1) …
```

**Для PLM:** если меняется базовая переменная — надо пересчитать все зависимые. В ваших файлах есть `МАССА`, `MASS`, `GR`.

### 4.9. GD&T и допуски

`BasFullData.dim_array → tol_ptr` — квалитеты (H7, k9, h8). `gtol` — позиционные допуски.

**Для PLM:** сравнение допусков двух ревизий — это аудит «H7 → H8».

### 4.10. Слои — смысловые

`DispCntrl.layer_array`: `AXES`, `CSYS`, `NOTES`, `PLANES`, `QUILTS`, `SURFS`, `DRAFTING_GEOM`, `DRAFT_DIMS`, `SOLID`.

**Для PLM:** если фичер добавлен в слой `NC_ASM_*` — это manufacturing; если в `DRAFT_DIMS` — это для чертежа.

### 4.11. Notes — заметки

`Notes` — текст. В drw — основная надпись, технические требования. В prt/asm — PMI-заметки.

**Для PLM:** парсить текст для аудита.

### 4.12. PMI — аннотации в 3D

`LargeText.annotation_planes` + `LargeText.notes` — 3D-аннотации (размеры, шероховатости, GTOL). Многие PLM не читают — а это важно для безбумажного производства.

### 4.13. Materials — материалы

`PTC_MATERIAL_NAME` (`STEEL_45`), `PTC_MATERIAL_DESCRIPTION` (`Сталь 45 ГОСТ 1050-88`), `МАТЕРИАЛ` (русское). Плюс свойства: `PTC_POISSON_RATIO`, `PTC_YOUNG_MODULUS`, `PTC_MASS_DENSITY`, `TEMPERATURE`.

**Для PLM:** нужно для расчётов и для сортамента.

### 4.14. Sheet metal — если есть

`FeatDefs` с `smt_*`, `smt_info` в `MdlStatus`, `bend_table`. Flat pattern.

**Для PLM:** развёртка — отдельный артефакт.

### 4.15. Welds — сварные швы

Как features в `AllFeatur` (`weld_sym`). Плюс `WeldSymbol` в drw.

**Для PLM:** сварная сборка — отдельный тип BOM.

### 4.16. NC-последовательности

`Mfg_info.step_arr` — список шагов обработки. Каждый шаг: tool, cut_feed, spindle_speed, depth.

**Для PLM:** маршрут изготовления. Это уже не BOM, а «process plan».

### 4.17. Массовые свойства (история)

`MpTypedData` в `MdlStatus` — старое/новое `PRO_MP_MASS`. Уже разобрали — можно строить график «как менялась масса» по ревизиям.

### 4.18. Audit trail с именами пользователей и компьютерами

`MdlStatus.mtrack_data` — уже разобрали. Для каждого rec — `user`, `computer`, `date`, `creo_ver`.

**Для PLM:** «кто последний трогал деталь».

### 4.19. Russian GOST / ЕСКД

В `drw` есть основная надпись с полями:
- `Изм.`, `Лист`, `№ докум.`, `Подп.`, `Дата`
- `Разраб.`, `Пров.`, `Т.контр.`, `Н.контр.`, `Утв.`
- `Лит.`, `Масса`, `Масштаб`
- `Лист`, `Листов`
- `Сталь 45 ГОСТ 1050-88`

**Для PLM:** это ЕСКД-шаблон. Можно строить автоматическую спецификацию.

### 4.20. Assembly bill of materials (BOM) на чертеже

`drw` содержит `type = SB_DRAWING` с таблицей `MASS_CM-TABL`. Это **сборочный чертёж** со спецификацией.

**Для PLM:** парсить таблицу → получать сборочную BOM.

### 4.21. Symbol instances на чертеже

`symbol_inst_xar` — все символы (основная надпись, допуски формы, шероховатости). Полезно для полного аудита.

### 4.22. View states (чертёж)

`ModelView` + `det_info_ptr` + `named_view_pzmatr` — какие виды есть на чертеже.

### 4.23. Zones (зоны чертежа)

`zone_id` — зоны A1, B2 на чертеже.

### 4.24. Layout (Notebook)

Top-down design: `Layout` = сборочный скелетон. `p_layout_ref` в `MdlRefInfo`. Если у вас используется — это master-файл для всей сборки.

### 4.25. Skeleton parts

Отдельный тип «скелетона» — задаёт общую геометрию для компонентов. `FeatDefsCmp` с `skeleton` flag.

### 4.26. UOBJ_ID — уникальный ID

В заголовке: `#- UOBJ_ID 1559910749 619524939 2058607588`. Это **три числа**, аналог UUID. Полезно для интеграции с внешними системами.

### 4.27. Revnum — номер ревизии

В `BasBasData.revnum_ptr → geom_revnum`, `cosm_revnum` — версии геометрии и косметики. Плюс `MdlStatus.rev_string` (`51801`, `51965`).

**Для PLM:** ключ для версионирования.

### 4.28. Thumbnail

`THMB_IMG_MAIN` — JPEG-превью 256×256. Для UI PLM — бесплатно.

## 5. Что бы я сделал как отдельные модули

```
creo_links.py      — BOM + upstream + mirror + family table
creo_graph.py      — единый граф, downstream/upstream, warnings
creo_mfg.py        — mfg (stock, fixture, tool, operation)
creo_configs.py    — simp_rep / exploded / publish
creo_relations.py  — formulas + зависимые параметры
creo_audit.py      — MdlStatus + user_time + mass changes (частично готово)
```

## 6. Приоритеты для PLM

| Приоритет | Что | Зачем |
|---|---|---|
| 🔴 1 | `instance_of` + `used_via_instance` | Связь generic → instance → сборки (ваш главный кейс) |
| 🔴 2 | `contains_via_instance` (BOM с instance) | BOM без instance — неполный |
| 🔴 3 | `mirror_of` + `inherit` | Связи «зеркало/наследование» — уже в ваших файлах (`06700423-01` и `_z`) |
| 🟠 4 | `mfg_stock_for` + `mfg_tool_for` + `mfg_fixture_for` | Manufacturing-связи |
| 🟠 5 | `saved_as` (rename / Save As) | Аудит переименований |
| 🟠 6 | `replace_by` | Замена компонентов |
| 🟠 7 | `drawing_of` + `drawing_shows_instance` | Связи чертежей |
| 🟠 8 | `simp_rep` | BOM по конфигурациям |
| 🟡 9 | `xref` (p_foreign_source) | Внешние ссылки |
| 🟡 10 | `publication` | Публикация геометрии |
| 🟡 11 | `flexible` / `envelope` | Гибкие/оболочки |
| 🟡 12 | relations (формулы) | Зависимые параметры |

## 7. Одна важная мысль

**BOM — не список `prt` в `asm`.** BOM — это:

```
(assembly, simp_rep) → [(component, instance, qty, simp_rep_of_component)]
```

Иначе generic болт в MASTER-конфигурации — один раз, а в SIMP_1 — не входит вовсе. И instance `M6x20` и `M6x30` — разные строки BOM, хотя generic один.

**Для ваших файлов:** в `06700423-01.asm` BOM = `[(06700423-01.prt, master, 1)]`. В `_z` stock не входит — это связь `mfg_stock_for`/`mirror_of`, не BOM.

## 8. Что реально можно проверить прямо сейчас

1. **Связь `mirror_of`** — в `06700423-01_z.prt` есть `MERGE_BASE_PART` с базой `226_595-223_985-136_3-01`. Это и есть «зеркало»/«stock» — можно проверить.

2. **Связь `saved_as`** — в `06700423-01.asm` в `MdlStatus.MdlStored.from_mdl_name = 226_595-223_985-01.ASM`, `to_mdl_name = 06700423-01.ASM`. Это «пересохранение с переименованием».

3. **Связь `inherit`** — в `06700423-01.prt` `MdlRefInfo.top_to_part_models.name = 226_595-223_985-136_3-01`.

4. **Связь `drawing_of`** — в `06700423-01.drw` `Dwg_Models.model_names = ['06700423-01.PRT']`.

5. **Связь `mfg_stock_for`** — в `06700423-01_z.prt` `MERGE_BASE_PART` = база, но в `06700423-01.prt` `ref_part_tab` → `226_595...`. То есть «01 сделана из 226…», «_z — stock для 01».

6. **Family table** — в ваших файлах пустая, но код `family_instances(raw)` готов. На реальном болте покажет `M6x20, M6x30, ...`.

## 9. Итог

Полная модель связей для PLM — **не иерархия, а типизированный граф** с 20+ типами рёбер. Ваш `creo_read.py` даёт «сырьё» (имена файлов, mtrack, params), `creo_history.py` — историю изменений, а новый `creo_links.py` + `creo_graph.py` — связи с типами и направлениями. Всё, что нужно для аудита и предупреждений («rename сломает X инстансов в Y сборках»), строится на этом графе.