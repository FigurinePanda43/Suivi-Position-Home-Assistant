"""Minimal ``.xlsx`` writer built on the standard library only.

An ``.xlsx`` file is a zip archive of XML documents (Office Open XML,
SpreadsheetML). This module writes the handful of parts needed for a clean,
typed workbook: several sheets, text / number / date / duration cells, a few
fixed styles (title, note, coloured headers, thin borders), column widths, frozen
header rows and auto filters.

It exists so that the Excel export never depends on a third-party package that
would have to be installed by hand on the Home Assistant host.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import io
from xml.sax.saxutils import escape
import zipfile

# --- Cell styles (indices in <cellXfs>) ---------------------------------------
STYLE_DEFAULT = 0
STYLE_TITLE = 1
STYLE_NOTE = 2
STYLE_HEADER_BLUE = 3
STYLE_HEADER_GREEN = 4
STYLE_TEXT = 5
STYLE_INT = 6
STYLE_DURATION = 7  # value = fraction of a day, shown as [h]:mm:ss
STYLE_DATETIME = 8  # value = Excel serial date, shown as dd/mm/yyyy hh:mm:ss
STYLE_DATETIME_SHORT = 9  # shown as dd/mm/yyyy hh:mm

_EXCEL_EPOCH = datetime(1899, 12, 30)
_NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_NS_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_XML_HEADER = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'

CellValue = str | int | float | datetime | None


def column_letter(index: int) -> str:
    """1 -> A, 26 -> Z, 27 -> AA."""
    letters = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def excel_serial(value: datetime) -> float:
    """Convert a naive datetime to an Excel serial date number."""
    return (value - _EXCEL_EPOCH).total_seconds() / 86400


def _attr(value: str) -> str:
    return escape(value, {'"': "&quot;"})


@dataclass(slots=True)
class Cell:
    """A cell value with its style index."""

    value: CellValue
    style: int = STYLE_DEFAULT


@dataclass(slots=True)
class Sheet:
    """A worksheet: sparse cells, column widths, frozen rows and auto filter."""

    name: str
    cells: dict[tuple[int, int], Cell] = field(default_factory=dict)
    col_widths: dict[int, float] = field(default_factory=dict)
    freeze_rows: int = 0
    autofilter: str | None = None

    def set(self, row: int, col: int, value: CellValue, style: int = STYLE_DEFAULT) -> None:
        """Set a cell (1-based row and column). ``None`` leaves the cell empty."""
        if value is None:
            return
        self.cells[(row, col)] = Cell(value, style)

    def set_widths(self, widths: tuple[float, ...] | list[float]) -> None:
        """Set the widths of columns A, B, C, ... in order."""
        for index, width in enumerate(widths, start=1):
            self.col_widths[index] = width

    @property
    def max_row(self) -> int:
        return max((row for row, _ in self.cells), default=1)

    @property
    def max_col(self) -> int:
        return max((col for _, col in self.cells), default=1)

    def _cell_xml(self, row: int, col: int, cell: Cell) -> str:
        ref = f"{column_letter(col)}{row}"
        style = f' s="{cell.style}"' if cell.style else ""
        value = cell.value
        if isinstance(value, datetime):
            return f'<c r="{ref}"{style}><v>{excel_serial(value)!r}</v></c>'
        if isinstance(value, bool):
            return f'<c r="{ref}"{style} t="b"><v>{int(value)}</v></c>'
        if isinstance(value, int | float):
            return f'<c r="{ref}"{style}><v>{value!r}</v></c>'
        text = str(value)
        space = ' xml:space="preserve"' if text != text.strip() else ""
        return f'<c r="{ref}"{style} t="inlineStr"><is><t{space}>{escape(text)}</t></is></c>'

    def to_xml(self, *, selected: bool) -> str:
        """Serialise the worksheet part."""
        rows: dict[int, list[tuple[int, Cell]]] = {}
        for (row, col), cell in self.cells.items():
            rows.setdefault(row, []).append((col, cell))

        parts = [
            _XML_HEADER,
            f'<worksheet xmlns="{_NS_MAIN}" xmlns:r="{_NS_REL}">',
            f'<dimension ref="A1:{column_letter(self.max_col)}{self.max_row}"/>',
            "<sheetViews>",
            f'<sheetView workbookViewId="0"{' tabSelected="1"' if selected else ""}>',
        ]
        if self.freeze_rows > 0:
            top_left = f"A{self.freeze_rows + 1}"
            parts.append(
                f'<pane ySplit="{self.freeze_rows}" topLeftCell="{top_left}" '
                'activePane="bottomLeft" state="frozen"/>'
                f'<selection pane="bottomLeft" activeCell="{top_left}" sqref="{top_left}"/>'
            )
        parts.append("</sheetView></sheetViews>")
        parts.append('<sheetFormatPr defaultRowHeight="15"/>')
        if self.col_widths:
            parts.append("<cols>")
            for index in sorted(self.col_widths):
                parts.append(
                    f'<col min="{index}" max="{index}" width="{self.col_widths[index]!r}" customWidth="1"/>'
                )
            parts.append("</cols>")
        parts.append("<sheetData>")
        for row in sorted(rows):
            parts.append(f'<row r="{row}">')
            for col, cell in sorted(rows[row], key=lambda item: item[0]):
                parts.append(self._cell_xml(row, col, cell))
            parts.append("</row>")
        parts.append("</sheetData>")
        if self.autofilter:
            parts.append(f'<autoFilter ref="{self.autofilter}"/>')
        parts.append(
            '<pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/>'
        )
        parts.append("</worksheet>")
        return "".join(parts)


_STYLES_XML = (
    _XML_HEADER + f'<styleSheet xmlns="{_NS_MAIN}">'
    '<numFmts count="3">'
    '<numFmt numFmtId="164" formatCode="[h]:mm:ss"/>'
    '<numFmt numFmtId="165" formatCode="dd/mm/yyyy hh:mm:ss"/>'
    '<numFmt numFmtId="166" formatCode="dd/mm/yyyy hh:mm"/>'
    "</numFmts>"
    '<fonts count="4">'
    '<font><sz val="11"/><name val="Calibri"/><family val="2"/></font>'
    '<font><b/><sz val="14"/><name val="Calibri"/><family val="2"/></font>'
    '<font><i/><sz val="9"/><color rgb="FF666666"/><name val="Calibri"/><family val="2"/></font>'
    '<font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/><family val="2"/></font>'
    "</fonts>"
    '<fills count="4">'
    '<fill><patternFill patternType="none"/></fill>'
    '<fill><patternFill patternType="gray125"/></fill>'
    '<fill><patternFill patternType="solid"><fgColor rgb="FF305496"/><bgColor indexed="64"/></patternFill></fill>'
    '<fill><patternFill patternType="solid"><fgColor rgb="FF548235"/><bgColor indexed="64"/></patternFill></fill>'
    "</fills>"
    '<borders count="2">'
    "<border><left/><right/><top/><bottom/><diagonal/></border>"
    "<border>"
    '<left style="thin"><color rgb="FFBFBFBF"/></left>'
    '<right style="thin"><color rgb="FFBFBFBF"/></right>'
    '<top style="thin"><color rgb="FFBFBFBF"/></top>'
    '<bottom style="thin"><color rgb="FFBFBFBF"/></bottom>'
    "<diagonal/>"
    "</border>"
    "</borders>"
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
    '<cellXfs count="10">'
    # 0 default
    '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
    # 1 title
    '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
    # 2 note
    '<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
    # 3 header blue
    '<xf numFmtId="0" fontId="3" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" '
    'applyBorder="1" applyAlignment="1">'
    '<alignment horizontal="center" vertical="center" wrapText="1"/></xf>'
    # 4 header green
    '<xf numFmtId="0" fontId="3" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" '
    'applyBorder="1" applyAlignment="1">'
    '<alignment horizontal="center" vertical="center" wrapText="1"/></xf>'
    # 5 text with border
    '<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1"/>'
    # 6 integer
    '<xf numFmtId="1" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1"/>'
    # 7 duration
    '<xf numFmtId="164" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1"/>'
    # 8 datetime
    '<xf numFmtId="165" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1"/>'
    # 9 datetime short
    '<xf numFmtId="166" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1"/>'
    "</cellXfs>"
    '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
    "</styleSheet>"
)


class Workbook:
    """A workbook made of :class:`Sheet` objects, serialised with :meth:`to_bytes`."""

    def __init__(self) -> None:
        self.sheets: list[Sheet] = []

    def add_sheet(self, name: str) -> Sheet:
        """Create a sheet. The caller is responsible for a valid, unique name."""
        sheet = Sheet(name=name)
        self.sheets.append(sheet)
        return sheet

    def _workbook_xml(self) -> str:
        sheets = "".join(
            f'<sheet name="{_attr(sheet.name)}" sheetId="{index}" r:id="rId{index}"/>'
            for index, sheet in enumerate(self.sheets, start=1)
        )
        defined_names = "".join(
            f'<definedName name="_xlnm._FilterDatabase" localSheetId="{index - 1}" hidden="1">'
            f"'{_attr(sheet.name.replace(chr(39), chr(39) * 2))}'!"
            f"{_absolute_ref(sheet.autofilter)}</definedName>"
            for index, sheet in enumerate(self.sheets, start=1)
            if sheet.autofilter
        )
        return (
            _XML_HEADER + f'<workbook xmlns="{_NS_MAIN}" xmlns:r="{_NS_REL}">'
            '<bookViews><workbookView activeTab="0"/></bookViews>'
            f"<sheets>{sheets}</sheets>"
            + (f"<definedNames>{defined_names}</definedNames>" if defined_names else "")
            + "</workbook>"
        )

    def _workbook_rels_xml(self) -> str:
        rels = "".join(
            f'<Relationship Id="rId{index}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{index}.xml"/>'
            for index in range(1, len(self.sheets) + 1)
        )
        styles_id = len(self.sheets) + 1
        return (
            _XML_HEADER + f'<Relationships xmlns="{_NS_PKG_REL}">{rels}'
            f'<Relationship Id="rId{styles_id}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
            'Target="styles.xml"/>'
            "</Relationships>"
        )

    def _content_types_xml(self) -> str:
        overrides = "".join(
            f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for index in range(1, len(self.sheets) + 1)
        )
        return (
            _XML_HEADER
            + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/styles.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            f"{overrides}</Types>"
        )

    @staticmethod
    def _root_rels_xml() -> str:
        return (
            _XML_HEADER + f'<Relationships xmlns="{_NS_PKG_REL}">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="xl/workbook.xml"/>'
            "</Relationships>"
        )

    def to_bytes(self) -> bytes:
        """Serialise the workbook to ``.xlsx`` bytes."""
        if not self.sheets:
            raise ValueError("A workbook needs at least one sheet")
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", self._content_types_xml())
            archive.writestr("_rels/.rels", self._root_rels_xml())
            archive.writestr("xl/workbook.xml", self._workbook_xml())
            archive.writestr("xl/_rels/workbook.xml.rels", self._workbook_rels_xml())
            archive.writestr("xl/styles.xml", _STYLES_XML)
            for index, sheet in enumerate(self.sheets, start=1):
                archive.writestr(
                    f"xl/worksheets/sheet{index}.xml", sheet.to_xml(selected=index == 1)
                )
        return output.getvalue()


def _absolute_ref(ref: str | None) -> str:
    """A1:H20 -> $A$1:$H$20."""
    if not ref:
        return ""
    cells = []
    for part in ref.split(":"):
        letters = "".join(ch for ch in part if ch.isalpha())
        digits = "".join(ch for ch in part if ch.isdigit())
        cells.append(f"${letters}${digits}")
    return ":".join(cells)
