# Пути решения дальше: формализация Mapping Table и извлечение Manufacturing-связей

## 1. Подтверждение гипотезы: `id_map_info_ptr` — это 16-битное LE-смещение

Судя по вашим же экспериментам:

- `map_table_explorer.py` читает **2 байта** (`struct.unpack('<H', ...)`) — и находит `10X1-D12`.
- `value_dumper_v3_specialized.py` читает **4 байта** (`struct.unpack('<I', ...)`) — и получает `Out of bounds`.

Причина: после `id_map_info_ptr\x00` идут **2 байта смещения**, а следующие 2 байта — это уже другое поле (`sw_info` или аналогичное). Поэтому 32-битное чтение захватывает мусор и даёт огромное число.

**Вывод:** `id_map_info_ptr` — это `uint16` little-endian, относительное смещение от начала `setup_data`. Это нужно зафиксировать в коде и в документации.

## 2. Что делать с таблицей: написать парсер `Mapping Table`

Нужно перейти от ручного поиска `10X1-D12` к автоматическому извлечению **всех** записей таблицы.

### 2.1. Функция `extract_mapping_table`

```python
import struct, re

def extract_mapping_table(data: bytes, setup_offset: int) -> list[dict]:
    """
    Извлекает записи из Mapping Table, на которую указывает id_map_info_ptr
    внутри setup_data.
    """
    # 1. Находим id_map_info_ptr в пределах setup_data
    #    (ограничим окно, например, 4096 байт от setup_offset)
    window = data[setup_offset:setup_offset + 4096]
    key = b'id_map_info_ptr\x00'
    idx = window.find(key)
    if idx == -1:
        return []

    # 2. Читаем 2 байта после \x00 как uint16 LE
    pos = idx + len(key)
    if pos + 2 > len(window):
        return []
    rel_offset = struct.unpack('<H', window[pos:pos+2])[0]

    # 3. Переходим по смещению
    table_start = setup_offset + rel_offset
    if table_start >= len(data):
        return []

    # 4. Определяем границы таблицы (эвристика: до следующего setup_data
    #    или до 2048 байт)
    next_setup = data.find(b'setup_data', table_start)
    table_end = next_setup if next_setup != -1 else min(len(data), table_start + 2048)
    table = data[table_start:table_end]

    # 5. Извлекаем все printable-строки длиной 3–64
    entries = []
    for m in re.finditer(rb'[\x20-\x7e]{3,64}', table):
        s = m.group().decode('latin-1', errors='ignore').strip()
        if not s:
            continue
        entries.append({
            'offset': table_start + m.start(),
            'raw': s,
            'type': classify_mfg_id(s),
        })
    return entries


def classify_mfg_id(s: str) -> str:
    """Эвристическая классификация ID."""
    if re.match(r'^\d+X\d+-\w+$', s):
        return 'fixture'
    if re.match(r'^T\d+$', s):
        return 'tool'
    if re.match(r'^(MACH|CNC|MACHINE)\w*$', s, re.I):
        return 'machine'
    if re.match(r'^[A-Z][A-Z0-9_\-]{2,}$', s):
        return 'operation_or_tool'
    return 'unknown'
```

### 2.2. Что это даёт

На `ctkd_738_01_001-01.prt.11` функция должна вернуть как минимум:

```python
[
  {'offset': ..., 'raw': '10X1-D12', 'type': 'fixture'},
  # возможно, 'T0010', 'FASKA', 'MACH01' и т.д.
]
```

Если `10X1-D12` не находится — значит, таблица содержит другие ID, или нужно расширить окно поиска (например, до 8192 байт), или таблица имеет другую структуру (например, строки с префиксом длины).

## 3. Углубить анализ: посмотреть на байты вокруг строки

Чтобы понять формат записей, нужно вывести hex-дамп **вокруг** найденной строки:

```python
def dump_around_string(data, table_start, target='10X1-D12', radius=32):
    idx = data.find(target.encode(), table_start)
    if idx == -1:
        print(f'{target} not found')
        return
    start = max(0, idx - radius)
    end = min(len(data), idx + len(target) + radius)
    chunk = data[start:end]
    print(f'Hex around {target} at 0x{idx:X}:')
    print(chunk.hex(' '))
    print('ASCII:', ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk))
```

Это покажет, есть ли перед строкой **длина** (1–2 байта) или **тип** (1 байт). Например:

- `\x08 10X1-D12` — длина 8.
- `\x01 \x08 10X1-D12` — тип 1, длина 8.
- `\x00 \x08 10X1-D12\x00` — null-terminated с префиксом.

Если структура подтвердится — можно написать точный парсер записей, а не просто `regex` по строкам.

## 4. Интеграция в `creo_links.py`: `_extract_mfg_links`

Как только парсер таблицы заработает, реализуйте `_extract_mfg_links`:

```python
def _extract_mfg_links(self):
    data = self.data
    links = []
    # Ищем все setup_data
    pos = 0
    while True:
        pos = data.find(b'setup_data', pos)
        if pos == -1:
            break
        # Извлекаем setup_id и appl_id (эвристически)
        setup_id = self._read_int_after(data, b'setup_id\x00', pos)
        appl_id  = self._read_int_after(data, b'appl_id\x00', pos)

        entries = extract_mapping_table(data, pos)
        for e in entries:
            if e['type'] == 'fixture':
                links.append(CreoEdge(
                    src=self.stem,
                    dst=e['raw'],
                    type='mfg_fixture_for',
                    meta={'setup_id': setup_id, 'appl_id': appl_id}
                ))
            elif e['type'] == 'tool':
                links.append(CreoEdge(
                    src=self.stem,
                    dst=e['raw'],
                    type='mfg_tool_for',
                    meta={'setup_id': setup_id}
                ))
            elif e['type'] == 'machine':
                links.append(CreoEdge(
                    src=self.stem,
                    dst=e['raw'],
                    type='mfg_machine_for',
                    meta={'setup_id': setup_id}
                ))
        pos += 1
    return links
```

Это закроет пункт `_extract_mfg_links` из `HANDOVER_TO_NEXT_AGENT.md`.

## 5. Обработка нескольких `setup_data`

В одном `.prt` может быть **несколько** `setup_data` (для разных операций/настроек). Нужно:

- Обрабатывать **все** вхождения `setup_data`.
- Для каждого извлекать свой `id_map_info_ptr` и свою таблицу.
- Связывать через `setup_id` / `appl_id`.

Если `setup_id` не читается эвристически — можно использовать порядковый номер (0, 1, 2…), но лучше найти поле `setup_id` в `setup_data` (оно там есть, судя по `ctkd_738_01_001-01.prt.11.txt`: `setup_type`, `setup_id`, `attr`, `appl_id`).

## 6. Тестирование и валидация

1. **Юнит-тест на `ctkd_738_01_001-01.prt.11`:**
   - `extract_mapping_table` должен вернуть запись с `raw == '10X1-D12'` и `type == 'fixture'`.

2. **Проверка на других файлах** из `Z:\PTC\Work\...`:
   - Если в файле есть manufacturing-данные, должны появиться `mfg_fixture_for`, `mfg_tool_for`, `mfg_machine_for`.
   - Если нет — список пустой (это нормально для чисто конструкторских деталей).

3. **Сравнение с `STATUS_REPORT.md`:**
   - Убедиться, что `10X1-D12` находится автоматически, а не вручную.

## 7. Что делать, если таблица имеет другую структуру

Если `10X1-D12` не находится в первых 2048 байтах после `table_start`, возможны варианты:

1. **Таблица больше** — расширить окно до 8192 или до следующего `setup_data`.
2. **Строки в UTF-16** — искать `\x00`-разделённые символы (маловероятно для ID, но возможно).
3. **Строки с префиксом длины** — тогда `regex` по `[\x20-\x7e]{3,64}` может захватывать лишнее. Нужно посмотреть hex и написать точный парсер.
4. **`id_map_info_ptr` указывает не на таблицу строк, а на структуру с указателями** — тогда нужно рекурсивно следовать по указателям. Но успех с `10X1-D12` говорит, что таблица содержит строки напрямую.

## 8. Дополнительно: использовать `strings` для быстрой проверки

Перед написанием парсера можно быстро проверить, какие строки есть в области таблицы:

```python
import subprocess
# Сохранить область таблицы в файл и прогнать strings
with open('table.bin', 'wb') as f:
    f.write(data[table_start:table_end])
subprocess.run(['strings', '-n', '3', 'table.bin'])
```

Это даст список всех строк — и вы увидите, есть ли там `10X1-D12`, `T0010`, `FASKA` и т.д.

## 9. Резюме: порядок действий

1. **Зафиксировать:** `id_map_info_ptr` — `uint16 LE` смещение от `setup_data`.
2. **Написать `extract_mapping_table`** (код выше).
3. **Проверить на `ctkd_738_01_001-01.prt.11`** — должен найти `10X1-D12`.
4. **Дампнуть hex вокруг строки** — понять формат записей (длина/тип/terminator).
5. **Уточнить парсер** под реальную структуру.
6. **Интегрировать в `creo_links.py`** как `_extract_mfg_links`.
7. **Прогнать на нескольких файлах** — убедиться, что не падает и находит связи.
8. **Добавить в тестовый набор** проверку, что `10X1-D12` извлекается автоматически.

Это снимет блокер из `STATUS_REPORT.md` и закроет пункт `_extract_mfg_links` из `HANDOVER_TO_NEXT_AGENT.md`.