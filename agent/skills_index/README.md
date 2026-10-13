# skills_index — поиск по СМЫСЛУ по дому (скиллы/инструменты/законы)

Семантический поиск: текст → вектор (`nomic-embed-text-v2-moe`, 768 чисел), ближайший по
смыслу. Задача — одной командой найти нужный скилл, не угадывая имя файла.

**Референс:** `D:\AI\repo\INDEX` (PowerShell, для тестов). Этот инструмент — самодостаточный
порт на Python: своя `db\`, настройки в папке, в живую базу пишем только publish.

## Три руки (закон манифеста)
- CLI: `skills_index.py build|search|status`
- Окно: `gui.py` (поиск + перестройка) — канон ui_common
- Визард: блок под щитом согласования

## Как работать
```
python skills_index.py build          # построить/обновить (инкремент; --full — полная)
python skills_index.py search "сделать коммит по правилам дома" --top 5
python skills_index.py status
```

## Корпус (настройка corpora)
`repo` (SKILL_*/.clinerules/MANIFEST/README/index.md) · `tools` (tools\agent *.py/*.md) ·
`agent_settings` (AGENT_SETTINGS) · `root` (D:\AI *.md/.clinerules). Шум — `exclude`.

## Правила
- Префиксы ОБЯЗАТЕЛЬНЫ: `search_document: ` индексация, `search_query: ` поиск.
- «В базу сразу не пишем»: сборка в `db\staging_<дата>.db`, publish = смена версии; прежняя
  БДа в `db\versions\`, чистка по `keep_versions`.
- Инкремент: неизменённые файлы (size+mtime) переиспользуют vec без пересчёта.
- База производная, в гит не идёт, пересобирается из файлов дома.

Класс Р: Creo и агент не нужны. Нужна модель эмбеддингов в Ollama.
