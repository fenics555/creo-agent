"""Чтение XLSX-файла спецификации без внешних зависимостей."""

from __future__ import annotations

import re
from io import BytesIO
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile


COLUMN_TITLES = {
    "формат": "format",
    "зона": "zone",
    "позиция": "position",
    "обозначение": "designation",
    "наименование": "name",
    "количество": "quantity",
    "примечание": "note",
}

KNOWN_SECTIONS = {
    "Документация",
    "Комплексы",
    "Сборочные единицы",
    "Детали",
    "Программные изделия и базы данных",
    "Стандартные изделия",
    "Прочие изделия",
    "Материалы",
    "Комплекты",
}

CELL_REFERENCE = re.compile(r"([A-Z]+)")


def _local_name(tag):
    return tag.rsplit("}", 1)[-1]


def _column_index(reference):
    match = CELL_REFERENCE.match(str(reference or "").upper())
    if not match:
        return 0
    result = 0
    for character in match.group(1):
        result = result * 26 + ord(character) - 64
    return result - 1


def _shared_strings(workbook):
    try:
        root = ElementTree.fromstring(workbook.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    result = []
    for item in root:
        if _local_name(item.tag) != "si":
            continue
        result.append("".join(
            node.text or "" for node in item.iter() if _local_name(node.tag) == "t"
        ))
    return result


def _first_worksheet_path(workbook):
    names = set(workbook.namelist())
    if "xl/worksheets/sheet1.xml" in names:
        return "xl/worksheets/sheet1.xml"
    worksheets = sorted(
        name for name in names
        if name.startswith("xl/worksheets/") and name.lower().endswith(".xml")
    )
    if not worksheets:
        raise ValueError("В XLSX отсутствуют листы")
    return worksheets[0]


def _cell_value(cell, shared_strings):
    cell_type = cell.get("t", "")
    if cell_type == "inlineStr":
        return "".join(
            node.text or "" for node in cell.iter() if _local_name(node.tag) == "t"
        )
    value_node = next(
        (node for node in cell if _local_name(node.tag) == "v"), None
    )
    value = value_node.text if value_node is not None and value_node.text is not None else ""
    if cell_type == "s" and value:
        try:
            return shared_strings[int(value)]
        except (ValueError, IndexError):
            return ""
    if cell_type == "b":
        return "Да" if value == "1" else "Нет"
    return value


def _worksheet_rows(workbook):
    shared_strings = _shared_strings(workbook)
    root = ElementTree.fromstring(workbook.read(_first_worksheet_path(workbook)))
    result = []
    for row in root.iter():
        if _local_name(row.tag) != "row":
            continue
        values = {}
        for cell in row:
            if _local_name(cell.tag) != "c":
                continue
            values[_column_index(cell.get("r"))] = _cell_value(cell, shared_strings)
        last_column = max(values, default=-1)
        result.append([values.get(index, "") for index in range(last_column + 1)])
    return result


def read_specification_xlsx(content):
    if not content:
        raise ValueError("Выбранный XLSX пуст")
    try:
        with ZipFile(BytesIO(content), "r") as workbook:
            table_rows = _worksheet_rows(workbook)
    except (BadZipFile, ElementTree.ParseError, KeyError) as error:
        raise ValueError("Файл не является корректным XLSX") from error
    if not table_rows:
        raise ValueError("В XLSX нет строк")

    headers = {}
    for index, value in enumerate(table_rows[0]):
        field = COLUMN_TITLES.get(str(value or "").strip().casefold())
        if field:
            headers[index] = field
    if "designation" not in headers.values() or "name" not in headers.values():
        raise ValueError("Не найдены столбцы «Обозначение» и «Наименование»")

    sections = []
    rows = []
    current_section = ""
    for values in table_rows[1:]:
        normalized = [str(value or "").strip() for value in values]
        if not any(normalized):
            continue
        first_value = normalized[0] if normalized else ""
        if first_value in KNOWN_SECTIONS and not any(normalized[1:]):
            current_section = first_value
            if current_section not in sections:
                sections.append(current_section)
            continue
        if not current_section:
            raise ValueError("Перед первой строкой элемента не указано название раздела")
        item = {field: "" for field in COLUMN_TITLES.values()}
        item["section"] = current_section
        for column_index, field in headers.items():
            if column_index < len(normalized):
                item[field] = normalized[column_index]
        if current_section == "Документация":
            item["quantity"] = ""
        rows.append(item)

    if not rows:
        raise ValueError("В XLSX не найдено элементов спецификации")
    return sections, rows
