# -*- coding: utf-8 -*-
r"""SPEC (единый блок): создание/чтение XLSX (Давыдовка) + связка с агентом:
секции по параметру ТИП, состав через CREOSON. Собран make_spec_one.py —
руками не править, править источники и перезапускать сборку."""
from __future__ import annotations
"""Чтение XLSX-файла спецификации без внешних зависимостей."""

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
"""Создание простого XLSX-файла спецификации без внешних зависимостей."""

import json
import os
import re
import tempfile
import time
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


INVALID_FILE_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
COLUMNS = (
    ("format", "Формат"),
    ("zone", "Зона"),
    ("position", "Позиция"),
    ("designation", "Обозначение"),
    ("name", "Наименование"),
    ("quantity", "Количество"),
    ("note", "Примечание"),
    ("image", "Изображение"),
)


def _parse_list(value, description):
    if not value:
        return []
    result = json.loads(value) if isinstance(value, str) else value
    if not isinstance(result, list):
        raise ValueError("Неверный формат %s" % description)
    return result


def _column_name(index):
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _inline_cell(reference, value):
    text = escape(str(value if value is not None else ""), {'"': "&quot;"})
    return '<c r="%s" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>' % (
        reference, text
    )


def _is_number(value):
    """Число из JSON отчёта: числовой параметр Creo, но не булево значение."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return value == value and value not in (float("inf"), float("-inf"))


def _number_text(value):
    if isinstance(value, float) and value.is_integer():
        return repr(int(value))
    return repr(value)


def _cell(reference, value):
    if _is_number(value):
        return '<c r="%s"><v>%s</v></c>' % (reference, _number_text(value))
    return _inline_cell(reference, value)


def _cell_text(value):
    if _is_number(value):
        return _number_text(value)
    return str(value if value is not None else "")


def _sheet_xml(table_rows, image_rows):
    xml_rows = []
    for row_index, values in enumerate(table_rows, 1):
        cells = "".join(
            _inline_cell("%s%d" % (_column_name(column_index), row_index), value)
            for column_index, value in enumerate(values, 1)
        )
        row_attributes = ' r="%d"' % row_index
        if row_index in image_rows:
            row_attributes += ' ht="80" customHeight="1"'
        xml_rows.append('<row%s>%s</row>' % (row_attributes, cells))
    last_row = max(1, len(table_rows))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<dimension ref="A1:H%d"/>' % last_row
        + '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="15"/>'
        '<cols>'
        '<col min="1" max="1" width="10" customWidth="1"/>'
        '<col min="2" max="3" width="11" customWidth="1"/>'
        '<col min="4" max="4" width="25" customWidth="1"/>'
        '<col min="5" max="5" width="42" customWidth="1"/>'
        '<col min="6" max="6" width="13" customWidth="1"/>'
        '<col min="7" max="7" width="28" customWidth="1"/>'
        '<col min="8" max="8" width="20" customWidth="1"/>'
        '</cols><sheetData>'
        + "".join(xml_rows)
        + '</sheetData>'
        + ('<drawing r:id="rId1"/>' if image_rows else '')
        + '</worksheet>'
    )


def _report_sheet_xml(table_rows, image_rows=None, image_column=None):
    image_rows = image_rows or {}
    column_count = max(1, max((len(row) for row in table_rows), default=1))
    row_count = max(1, len(table_rows))
    widths = []
    for column_index in range(column_count):
        longest = max(
            (
                len(_cell_text(row[column_index] if column_index < len(row) else ""))
                for row in table_rows
            ),
            default=0,
        )
        width = max(10, min(60, longest + 2))
        if image_column is not None and column_index == image_column:
            width = max(20, width)
        widths.append(width)
    columns_xml = "".join(
        '<col min="%d" max="%d" width="%s" customWidth="1"/>'
        % (index, index, width)
        for index, width in enumerate(widths, 1)
    )
    rows_xml = []
    for row_index, row in enumerate(table_rows, 1):
        cells = "".join(
            _cell(
                "%s%d" % (_column_name(column_index), row_index),
                row[column_index - 1] if column_index <= len(row) else "",
            )
            for column_index in range(1, column_count + 1)
        )
        row_attributes = ' r="%d"' % row_index
        if row_index in image_rows:
            row_attributes += ' ht="80" customHeight="1"'
        rows_xml.append('<row%s>%s</row>' % (row_attributes, cells))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<dimension ref="A1:%s%d"/>' % (_column_name(column_count), row_count)
        + '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="15"/><cols>'
        + columns_xml
        + '</cols><sheetData>'
        + "".join(rows_xml)
        + '</sheetData><autoFilter ref="A1:%s%d"/>' % (_column_name(column_count), row_count)
        + ('<drawing r:id="rId1"/>' if image_rows else '')
        + '</worksheet>'
    )


def _table_rows(sections, rows, image_paths, assembly_model_name=""):
    result = [[title for _, title in COLUMNS]]
    image_rows = {}
    assembly_image = image_paths.get(str(assembly_model_name or "").strip().lower())
    if assembly_image:
        result.append([""] * len(COLUMNS))
        image_rows[len(result)] = assembly_image
    used_row_ids = set()

    def append_item(row):
        result.append([
            str(row.get(field) or "") if field != "image" else ""
            for field, _ in COLUMNS
        ])
        model_name = str(row.get("modelName") or "").strip().lower()
        image_path = image_paths.get(model_name)
        if image_path:
            image_rows[len(result)] = image_path

    for section in sections:
        if not isinstance(section, dict):
            continue
        section_name = str(section.get("name") or "").strip()
        section_rows = [
            row for row in rows
            if isinstance(row, dict) and str(row.get("section") or "").strip() == section_name
        ]
        if not section_name or not section_rows:
            continue
        result.append([section_name] + [""] * (len(COLUMNS) - 1))
        for row in section_rows:
            used_row_ids.add(id(row))
            append_item(row)
    remaining_rows = [row for row in rows if isinstance(row, dict) and id(row) not in used_row_ids]
    for row in remaining_rows:
        append_item(row)
    return result, image_rows


def _jpeg_dimensions(image_path):
    """Return JPEG width and height without requiring an external library."""
    try:
        with open(image_path, "rb") as image_file:
            if image_file.read(2) != b"\xff\xd8":
                return None
            while True:
                prefix = image_file.read(1)
                if not prefix:
                    return None
                if prefix != b"\xff":
                    continue
                marker = image_file.read(1)
                while marker == b"\xff":
                    marker = image_file.read(1)
                if not marker or marker in (b"\xd8", b"\xd9"):
                    continue
                length_data = image_file.read(2)
                if len(length_data) != 2:
                    return None
                segment_length = int.from_bytes(length_data, "big")
                if segment_length < 2:
                    return None
                if marker[0] in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    size_data = image_file.read(5)
                    if len(size_data) != 5:
                        return None
                    height = int.from_bytes(size_data[1:3], "big")
                    width = int.from_bytes(size_data[3:5], "big")
                    return (width, height) if width > 0 and height > 0 else None
                image_file.seek(segment_length - 2, os.SEEK_CUR)
    except (OSError, TypeError, ValueError):
        return None


def _drawing_xml(image_rows, column_index=7):
    anchors = []
    for picture_index, (row_index, image_path) in enumerate(sorted(image_rows.items()), 1):
        box_left = 38100
        box_top = 38100
        box_right = 1000000
        box_bottom = 950000
        dimensions = _jpeg_dimensions(image_path)
        if dimensions:
            image_width, image_height = dimensions
            box_width = box_right - box_left
            box_height = box_bottom - box_top
            if image_width * box_height >= image_height * box_width:
                drawing_width = box_width
                drawing_height = max(1, round(box_width * image_height / image_width))
            else:
                drawing_height = box_height
                drawing_width = max(1, round(box_height * image_width / image_height))
            box_left += (box_width - drawing_width) // 2
            box_top += (box_height - drawing_height) // 2
            box_right = box_left + drawing_width
            box_bottom = box_top + drawing_height
        anchors.append(
            '<xdr:twoCellAnchor editAs="twoCell">'
            '<xdr:from><xdr:col>%d</xdr:col><xdr:colOff>%d</xdr:colOff>'
            '<xdr:row>%d</xdr:row><xdr:rowOff>%d</xdr:rowOff></xdr:from>'
            '<xdr:to><xdr:col>%d</xdr:col><xdr:colOff>%d</xdr:colOff>'
            '<xdr:row>%d</xdr:row><xdr:rowOff>%d</xdr:rowOff></xdr:to>'
            '<xdr:pic><xdr:nvPicPr><xdr:cNvPr id="%d" name="Изображение %d"/>'
            '<xdr:cNvPicPr><a:picLocks noChangeAspect="1"/></xdr:cNvPicPr></xdr:nvPicPr>'
            '<xdr:blipFill><a:blip r:embed="rId%d"/>'
            '<a:stretch><a:fillRect/></a:stretch></xdr:blipFill>'
            '<xdr:spPr><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></xdr:spPr></xdr:pic>'
            '<xdr:clientData fLocksWithSheet="1" fPrintsWithSheet="1"/></xdr:twoCellAnchor>'
            % (
                column_index, box_left, row_index - 1, box_top,
                column_index, box_right, row_index - 1, box_bottom,
                picture_index, picture_index, picture_index,
            )
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        + "".join(anchors) + '</xdr:wsDr>'
    )


def _drawing_relationships(image_rows):
    relationships = []
    for image_index, _ in enumerate(sorted(image_rows.items()), 1):
        relationships.append(
            '<Relationship Id="rId%d" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
            'Target="../media/image%d.jpg"/>' % (image_index, image_index)
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(relationships) + '</Relationships>'
    )


def create_xlsx(
        directory, designation, sections=None, rows=None, images=None,
        assembly_model_name=None
):
    directory_text = str(directory or "").strip()
    designation_text = str(designation or "").strip()
    if not directory_text:
        raise ValueError("Creo не вернул папку открытой сборки")
    if not designation_text:
        raise ValueError("У открытой сборки не заполнено обозначение")
    if INVALID_FILE_NAME.search(designation_text) or designation_text.endswith((" ", ".")):
        raise ValueError("Обозначение содержит недопустимые для имени файла символы")

    target_directory = Path(directory_text)
    if target_directory.is_file():
        target_directory = target_directory.parent
    if not target_directory.is_absolute() or not target_directory.is_dir():
        raise ValueError("Папка открытой сборки не найдена: %s" % directory_text)

    parsed_sections = _parse_list(sections, "разделов")
    parsed_rows = _parse_list(rows, "строк")
    parsed_images = _parse_list(images, "изображений")
    image_candidates = []
    for image in parsed_images:
        if not isinstance(image, dict):
            continue
        model_name = str(image.get("modelName") or "").strip().lower()
        image_path = Path(str(image.get("path") or "").strip())
        if model_name and image_path.suffix.lower() in (".jpg", ".jpeg"):
            image_candidates.append((model_name, image_path))
    if image_candidates:
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline and not all(path.is_file() for _, path in image_candidates):
            time.sleep(0.05)
    image_paths = {
        model_name: image_path
        for model_name, image_path in image_candidates
        if image_path.is_file()
    }
    table_rows, image_rows = _table_rows(
        parsed_sections, parsed_rows, image_paths, assembly_model_name
    )
    file_name = designation_text if designation_text.lower().endswith(".xlsx") else designation_text + ".xlsx"
    output_path = target_directory / file_name

    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(
                prefix=".creo_spec_", suffix=".xlsx.tmp", dir=target_directory, delete=False
        ) as temporary_file:
            temporary_name = temporary_file.name
        with ZipFile(temporary_name, "w", ZIP_DEFLATED) as workbook:
            workbook.writestr("[Content_Types].xml", (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Default Extension="jpg" ContentType="image/jpeg"/>'
                '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                + ('<Override PartName="/xl/drawings/drawing1.xml" ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/>' if image_rows else '')
                +
                '</Types>'
            ))
            workbook.writestr("_rels/.rels", (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                '</Relationships>'
            ))
            workbook.writestr("xl/workbook.xml", (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                '<sheets><sheet name="Спецификация" sheetId="1" r:id="rId1"/></sheets></workbook>'
            ))
            workbook.writestr("xl/_rels/workbook.xml.rels", (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
                '</Relationships>'
            ))
            workbook.writestr("xl/worksheets/sheet1.xml", _sheet_xml(table_rows, image_rows))
            if image_rows:
                workbook.writestr("xl/worksheets/_rels/sheet1.xml.rels", (
                    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing" '
                    'Target="../drawings/drawing1.xml"/></Relationships>'
                ))
                workbook.writestr("xl/drawings/drawing1.xml", _drawing_xml(image_rows))
                workbook.writestr("xl/drawings/_rels/drawing1.xml.rels", _drawing_relationships(image_rows))
                for image_index, (_, image_path) in enumerate(sorted(image_rows.items()), 1):
                    workbook.write(image_path, "xl/media/image%d.jpg" % image_index)
        os.replace(temporary_name, output_path)
        temporary_name = None
    finally:
        if temporary_name:
            try:
                os.unlink(temporary_name)
            except OSError:
                pass
        target_resolved = target_directory.resolve()
        for image_path in set(image_paths.values()):
            try:
                image_resolved = image_path.resolve()
                if (
                    image_resolved.parent == target_resolved
                    and image_resolved.name.startswith("creo_excel_image_")
                ):
                    image_resolved.unlink(missing_ok=True)
            except OSError:
                pass
    return output_path, len(parsed_rows), len(image_rows)


def _normalized_report_value(value):
    """Числа сохраняются числами, остальное приводится к тексту."""
    if _is_number(value):
        return value
    return str(value if value is not None else "")


def create_report_xlsx(
        directory, assembly_name, columns=None, rows=None, images=None,
        model_names=None, image_column=None
):
    directory_text = str(directory or "").strip()
    if not directory_text:
        raise ValueError("Creo не вернул рабочую папку")
    target_directory = Path(directory_text)
    if not target_directory.is_absolute() or not target_directory.is_dir():
        raise ValueError("Рабочая папка Creo не найдена: %s" % directory_text)

    parsed_columns = _parse_list(columns, "столбцов отчёта")
    parsed_rows = _parse_list(rows, "строк отчёта")
    parsed_images = _parse_list(images, "изображений отчёта")
    parsed_model_names = _parse_list(model_names, "имён моделей отчёта")
    if not parsed_columns:
        raise ValueError("В отчёте нет столбцов")
    headers = [str(value if value is not None else "") for value in parsed_columns]
    normalized_rows = []
    for row in parsed_rows:
        if not isinstance(row, list):
            raise ValueError("Неверный формат строки отчёта")
        normalized_rows.append([
            _normalized_report_value(row[index] if index < len(row) else None)
            for index in range(len(headers))
        ])

    base_name = re.sub(r"\.(?:asm|prt|drw)(?:\.\d+)?$", "", str(assembly_name or ""), flags=re.I)
    base_name = INVALID_FILE_NAME.sub("_", base_name).strip(" .") or "creo_report"
    output_path = target_directory / (base_name + "_report.xlsx")
    table_rows = [headers] + normalized_rows
    try:
        image_column_index = int(image_column)
    except (TypeError, ValueError):
        image_column_index = -1
    if image_column_index < 0 or image_column_index >= len(headers):
        image_column_index = None
    image_candidates = []
    for image in parsed_images:
        if not isinstance(image, dict):
            continue
        model_name = str(image.get("modelName") or "").strip().lower()
        image_path = Path(str(image.get("path") or "").strip())
        if model_name and image_path.suffix.lower() in (".jpg", ".jpeg"):
            image_candidates.append((model_name, image_path))
    if image_candidates:
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline and not all(path.is_file() for _, path in image_candidates):
            time.sleep(0.05)
    image_paths = {
        model_name: image_path for model_name, image_path in image_candidates if image_path.is_file()
    }
    image_rows = {}
    if image_column_index is not None:
        for row_index, model_name in enumerate(parsed_model_names, 2):
            image_path = image_paths.get(str(model_name or "").strip().lower())
            if image_path and row_index <= len(table_rows):
                image_rows[row_index] = image_path
    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(
                prefix=".creo_report_", suffix=".xlsx.tmp", dir=target_directory, delete=False
        ) as temporary_file:
            temporary_name = temporary_file.name
        with ZipFile(temporary_name, "w", ZIP_DEFLATED) as workbook:
            workbook.writestr("[Content_Types].xml", (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Default Extension="jpg" ContentType="image/jpeg"/>'
                '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                + ('<Override PartName="/xl/drawings/drawing1.xml" ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/>' if image_rows else '')
                +
                '</Types>'
            ))
            workbook.writestr("_rels/.rels", (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                '</Relationships>'
            ))
            workbook.writestr("xl/workbook.xml", (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                '<sheets><sheet name="Отчёт" sheetId="1" r:id="rId1"/></sheets></workbook>'
            ))
            workbook.writestr("xl/_rels/workbook.xml.rels", (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
                '</Relationships>'
            ))
            workbook.writestr(
                "xl/worksheets/sheet1.xml",
                _report_sheet_xml(table_rows, image_rows, image_column_index),
            )
            if image_rows:
                workbook.writestr("xl/worksheets/_rels/sheet1.xml.rels", (
                    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing" '
                    'Target="../drawings/drawing1.xml"/></Relationships>'
                ))
                workbook.writestr(
                    "xl/drawings/drawing1.xml",
                    _drawing_xml(image_rows, image_column_index),
                )
                workbook.writestr(
                    "xl/drawings/_rels/drawing1.xml.rels",
                    _drawing_relationships(image_rows),
                )
                for image_index, (_, image_path) in enumerate(sorted(image_rows.items()), 1):
                    workbook.write(image_path, "xl/media/image%d.jpg" % image_index)
        os.replace(temporary_name, output_path)
        temporary_name = None
    finally:
        if temporary_name:
            try:
                os.unlink(temporary_name)
            except OSError:
                pass
        target_resolved = target_directory.resolve()
        for image_path in set(image_paths.values()):
            try:
                image_resolved = image_path.resolve()
                if image_resolved.parent == target_resolved and image_resolved.name.startswith("creo_excel_image_"):
                    image_resolved.unlink(missing_ok=True)
            except OSError:
                pass
    return output_path, len(normalized_rows), len(image_rows)

import os
import creo_tools as CT

def _sec_by_type(v):
    t = str(v or "").strip().upper()
    return {"ДОКУМЕНТ": "Документация", "КОМПЛЕКС": "Комплексы", "СБОРКА": "Сборочные единицы",
            "ДЕТАЛЬ": "Детали", "СТАНДАРТНОЕ": "Стандартные изделия", "ПРОЧЕЕ": "Прочие изделия",
            "МАТЕРИАЛ": "Материалы", "КОМПЛЕКТ": "Комплекты"}.get(t, "")

def _pval(plist, names):
    want = [n.upper() for n in names]
    for p in plist:
        if str(p.get("name", "")).upper() in want:
            return p.get("value")
    return None

def _params_of(f):
    j = CT.creo_call("parameter", "list", {"file": f}, 20)
    if not CT.ok(j):
        return []
    return (j.get("data") or {}).get("param_list") or (j.get("data") or {}).get("paramlist") or []

def tool_spec_create_active(**kw):
    act = CT.tool_get_active()
    if not act:
        return "нет активной модели в Creo"
    wd = CT.tool_pwd()
    base = re.sub(r"\.(asm|prt|drw)(\.\d+)?$", "", act, flags=re.I)
    ap = _params_of(act)
    designation = str(_pval(ap, ["ОБОЗНАЧЕНИЕ", "DESIGNATION"]) or base)
    j = CT.creo_call("bom", "get_paths", {"file": act, "paths": False, "top_level": False, "exclude_inactive": True}, 30)
    root = (j.get("data") or {}) if CT.ok(j) else {}
    seen, comps, stack = set(), [], list(CT._kids(root))
    while stack:
        node = stack.pop()
        if not isinstance(node, dict):
            continue
        f = str(node.get("file") or "")
        if f and f not in seen:
            seen.add(f); comps.append(f)
        stack.extend(CT._kids(node))
    if not comps:
        return "сборка пуста или BOM не прочитался"
    rows = []
    for f in comps:
        pl = _params_of(f)
        sec = _sec_by_type(_pval(pl, ["ТИП"])) or ("Сборочные единицы" if f.lower().endswith(".asm") else "Детали")
        rows.append({"section": sec,
                     "format": str(_pval(pl, ["ФОРМАТ", "FORMAT"]) or ""),
                     "zone": str(_pval(pl, ["ЗОНА", "ZONE"]) or ""),
                     "position": str(_pval(pl, ["ПОЗИЦИЯ", "POSITION"]) or ""),
                     "designation": "" if sec == "Стандартные изделия" else str(_pval(pl, ["ОБОЗНАЧЕНИЕ", "DESIGNATION"]) or re.sub(r"\.(asm|prt|drw)(\.\d+)?$", "", f, flags=re.I)),
                     "name": str(_pval(pl, ["НАИМЕНОВАНИЕ", "NAME"]) or ""),
                     "quantity": "1",
                     "note": str(_pval(pl, ["ПРИМЕЧАНИЕ", "NOTE"]) or "")})
    canon = ["Документация", "Комплексы", "Сборочные единицы", "Детали", "Стандартные изделия", "Прочие изделия", "Материалы", "Комплекты"]
    used = [{"name": c} for c in canon if any(r["section"] == c for r in rows)]
    try:
        out, n_rows, n_img = create_xlsx(wd, designation, used, rows, [], act)
    except ValueError as e:
        return "XLSX не создан: %s" % e
    return "спецификация записана: %s (строк: %d, картинок: %d)" % (out, n_rows, n_img)

def tool_spec_read(path="", **kw):
    p = (path or "").strip().strip('"')
    if not p or not os.path.isfile(p):
        return "укажи существующий путь к XLSX"
    try:
        with open(p, "rb") as f:
            sections, rows = read_specification_xlsx(f.read())
    except ValueError as e:
        return "ошибка XLSX: %s" % e
    out = ["разделы: " + ", ".join(sections), "строк: %d" % len(rows)]
    out += ["- [%s] %s | %s | кол %s" % (r.get("section"), r.get("designation"), r.get("name"), r.get("quantity")) for r in rows[:25]]
    if len(rows) > 25:
        out.append("…и ещё %d" % (len(rows) - 25))
    return "\n".join(out)

TOOLS = [
    {"name": "spec_create_active", "desc": "ГОСТ-спецификация (XLSX) в папку сборки из живого Creo: разделы по ТИП, состав по BOM", "params": {}, "approval": True, "fn": tool_spec_create_active},
    {"name": "spec_read", "desc": "Прочитать XLSX-спецификацию: разделы и строки", "params": {"path": "путь к xlsx"}, "approval": False, "fn": tool_spec_read},
]
