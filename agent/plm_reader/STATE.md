# STATE — ЖИВОЕ СОСТОЯНИЕ PLM READER (обновлять при КАЖДОМ шаге)

> Правило: «Сессия смертна. Всё, что не в файле — потеряно».
> **Обновлено:** 30.10.2026, фаза 38 · нога Cline (V141: новый сканер + Database + схема 25 таблиц)

## 🔴🔴 ГЛАВНОЕ ЭТОЙ НОГИ (V141)

### 1. СХЕМА СКАНЕРА — ДВА ХОДА (закон владельца, §184)
```
① ЧИТАЕМ В RAM:   файл (Z:) → байты в ПАМЯТЬ
② ИЗ RAM → БАЗА:  разбор (ящики) → запись
③ RAM освобождается
⇒ ДИСКОВЫЙ КЕШ ЗАПРЕЩЁН (= копия файлов, 42 ГБ!)
```
**Рычаг отладки** (`dump_raw_dir`) — ВНУТРИ сканера (`read_file`).
**Пропуск неизменившихся** (`size`+`mtime`) — по умолчанию; `full=true` — «перечитать всё».

### 2. НОВЫЙ СКАНЕР (`debug\scanner_plm.py`, 56 КБ)
```
scan_item_new(path) → 16 ЯЩИКОВ:
   snapshots · mass_props · bodies · materials · master_mat · tools ·
   features · dimensions · equations · health · params · unknown_fields ·
   matrices · drawing · links · media
```
**ФОРМУЛЫ (доказаны):**
- **МАССА = `mass_prop.volume × density`** (сверено с J-Link **16/16**)
- **НОМИНАЛ = `2F B1 B2`** → double `40 B1 B2 00…`
- **ТИП = `feat_defs_<N> − 910`** (словарь 314)
- **ИМЯ МАТЕРИАЛА = `PTC_MASTER_MATERIAL` → `65G_MMKGS`** (сталь 65Г!)

### 3. DATABASE (`debug\plm_database.py`)
```
stats · check · validate <draft> · publish <draft> · indexes · vacuum · backup
```
**Публикация — через `engine._publish()`** (бэкап + versioned + атомарная подмена).

### 4. СХЕМА БОЕВОЙ БАЗЫ — 25 ТАБЛИЦ (в `engine.SCHEMA`)
```
НОВЫЕ: items · item_ver · bodies · materials · master_mat · tools ·
       unknown_fields · dim_all · matrices · drawing · components
СТАРЫЕ: snapshots · params · history · links · derived · family · folders ·
        changes · health · props · meta · mass_props · dimensions · features · equations
```

### 5. УНИКАЛЬНОСТЬ (замер: 47 389 файлов → 24 267 имён!)
```
ИЗДЕЛИЕ (item_key = folder + '\' + model)  ← УНИКАЛЬНЫЙ
   └─ ВЕРСИЯ (.prt.N)  └─ ФАЙЛ (path)
КОМПЛЕКТ: .prt + .asm + .drw = ОДНО ИЗДЕЛИЕ!
```

### 6. ПЕРЕКЛЮЧАТЕЛЬ В `engine.do_scan`
```
scanner_new   = False  → старый scan_item (по умолчанию, безопасно)
scanner_extra = True   → доп. таблицы нового сканера
```

## 📊 ПРОВЕРЕНО (боевой тест)
```
2 папки · 19 файлов · 26 840 строк · 0.38 с
items 9 · bodies 17 · materials 14 (STAL_45 · STEEL_40X · 65G) · matrices 1868
```

## 🔴 ГРАБЛИ НОГИ
| # | Грабля | Лечение |
|---|---|---|
| 1 | **V140 == V140** → «обновлений нет» | **поднимать APP_VERSION!** (§6.8) |
| 2 | `make_version_json.py` **стирает notes** | восстанавливать вручную |
| 3 | `re.S` ломает `\xe0\x0a` | не использовать `re.S` |
| 4 | класс `[\xc0-\xff]` не берёт кириллицу | `[\x80-\xff]` |
| 5 | `f8 <N>` бывает многобайтной (`80 90`=144) | читать число целиком |
| 6 | `values` — зарезервировано SQL | переименовать в `vals` |
| 7 | **«мусора» в файлах НЕТ** (закон!) | собирать ВСЁ |
| 8 | **имена произвольны** | смысл — из чисел |

## 🎯 ЧТО ОСТАЛОСЬ
| # | Что |
|---|---|
| 1 | **Полный скан склада** (70 000 файлов) — владелец |
| 2 | Реестр «не разобрано» — 18 пунктов |
| 3 | Оптимизация `unknown_fields` (3.4 мс) |
| 4 | Переключение `scanner_new = True` |
