import hashlib
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pdfplumber

# Source PDF
TALLA_2024_PATH = Path("data/raw/talla_2024.pdf")
TALLA_2024_URL = "https://portal.siinsan.gob.gt/archivos/censo_02.pdf"
TALLA_2024_SHA256 = "d3eb1c112cd3f5480aa8180a3573234f19ae4c0c95218e5f416d4751d762eea2"
ISSUES_URL = "https://github.com/JulianKeerl/guatemala-municipal-atlas/issues"

# Annex 4 Layout: the table is printed twice, one table has the font size 5.6pt (the one
# that we use as it is the one that lines up with the visible grid) and one at 7.0pt
# Department headings are bold and at 7.3 pt font size
TABLE_FONT_SIZE = 5.6
TABLE_FONT_NAME = "Aptos"
DEPARTMENT_FONT_SIZE = 7.3
DEPARTMENT_FONT_NAME = "Aptos-Bold"

FONT_SIZE_TOLERANCE = 0.1
MAX_COLUMN_DISTANCE = 8.0

# Right edge (x1) of each number column, even pages are shifted
ODD_PAGE_COLUMNS: dict[str, float] = {
    "n_1986": 191.3,
    "pct_1986": 212.1,
    "n_2001": 235.9,
    "pct_2001": 256.7,
    "diff_2001_1986": 282.2,
    "n_2008": 312.7,
    "pct_2008": 333.6,
    "diff_2008_2001": 362.1,
    "n_2015": 393.3,
    "pct_2015": 409.7,
    "diff_2015_2008": 433.5,
    "n_2024": 461.4,
    "pct_2024": 484.5,
    "diff_2024_2015": 510.6,
    "diff_2024_1986": 545.6,
}
EVEN_PAGE_COLUMNS: dict[str, float] = {
    "n_1986": 154.3,
    "pct_1986": 177.4,
    "n_2001": 198.9,
    "pct_2001": 222.1,
    "diff_2001_1986": 247.6,
    "n_2008": 275.7,
    "pct_2008": 298.9,
    "diff_2008_2001": 327.5,
    "n_2015": 356.3,
    "pct_2015": 373.5,
    "diff_2015_2008": 398.9,
    "n_2024": 426.8,
    "pct_2024": 448.4,
    "diff_2024_2015": 474.9,
    "diff_2024_1986": 510.9,
}

# Types
type Word = dict[str, Any]
type PdfObject = dict[str, Any]
type Position = tuple[int, int]


@dataclass
class TableLine:
    """A raw line of the table: a row, a heading or half a wrapped name."""

    row_id: int | None  # None for headings and names that are multiline
    name: str
    values: dict[str, float]
    is_department: bool


@dataclass
class TableRow:
    """One row of the table: a municipio/zone, with its values."""

    row_id: int
    name: str
    values: dict[str, float]


def verify_pdf(pdf_path: Path, pdf_url: str, expected_sha256: str) -> None:
    """Check that the pdf exists and is the expected version."""
    if not pdf_path.exists():
        raise FileNotFoundError(f"{pdf_path} not found. Download it from {pdf_url}")

    with open(pdf_path, "rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()

    if digest != expected_sha256:
        raise ValueError(
            f"{pdf_path} is not the expected version (sha256 {digest[:12]}…).\n"
            f"Re-download it from {pdf_url}. If it still fails, the report was "
            f"probably updated: please open an issue at {ISSUES_URL}"
        )


def matches_style(pdf_object: PdfObject, font_name: str, font_size: float) -> bool:
    """Return true if pdf object is a character in the given font and size."""
    if pdf_object["object_type"] != "char":
        return False

    fontname_check = pdf_object["fontname"].endswith(font_name)
    fontsize_check = math.isclose(
        pdf_object["size"], font_size, abs_tol=FONT_SIZE_TOLERANCE
    )

    return fontname_check and fontsize_check


def is_table_text(pdf_object: PdfObject) -> bool:
    """Return True for chars in the Annex 4 table, skipping its overlaid duplicate."""
    return matches_style(pdf_object, TABLE_FONT_NAME, TABLE_FONT_SIZE)


def is_department_text(pdf_object: PdfObject) -> bool:
    """Return True for characters of the bold department headings."""
    return matches_style(pdf_object, DEPARTMENT_FONT_NAME, DEPARTMENT_FONT_SIZE)


def parse_number(text: str) -> float | None:
    """Return the value of a table number like "1,804" or "-8.7", or None."""
    try:
        # remove the thousands separators ','
        return float(text.replace(",", ""))
    except ValueError:
        return None


def parse_line(words: list[Word], columns: dict[str, float]) -> TableLine:
    """Splits one raw line of the table into a table line"""
    words = sorted(words, key=lambda w: w["x0"])

    # A row starts with an id number, however line wrappings can occur, in those
    # instances we set it to None
    row_id: int | None = None
    if words[0]["text"].isdigit():
        row_id = int(words[0]["text"])
        words = words[1:]

    is_department = words[0]["fontname"].endswith(DEPARTMENT_FONT_NAME)
    name_parts: list[str] = []
    values: dict[str, float] = {}
    for word in words:
        value = parse_number(word["text"])
        nearest_column = min(columns, key=lambda c: abs(columns[c] - word["x1"]))
        if (
            value is not None
            and abs(columns[nearest_column] - word["x1"]) < MAX_COLUMN_DISTANCE
        ):
            values[nearest_column] = value
        else:
            name_parts.append(word["text"])

    return TableLine(
        row_id=row_id,
        name=" ".join(name_parts),
        values=values,
        is_department=is_department,
    )


def read_lines(pdf_path: Path) -> list[tuple[Position, list[Word]]]:
    """Group the table's words into lines, in reading order.
    Keeps the table rows and the department headings, sorted by (page number,top).
    """

    lines: defaultdict[Position, list[Word]] = defaultdict(list)
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[166:176]:  # these pages have the actual data and tables
            filtered_page = page.filter(
                lambda obj: is_table_text(obj) or is_department_text(obj)
            )
            # extra_attrs is necessary here so we can still tell apart department names
            # and table entries based on fontname
            for word in filtered_page.extract_words(extra_attrs=["fontname"]):
                lines[(page.page_number, round(word["top"]))].append(word)
    return sorted(lines.items())


def join_wrapped_names(parsed: list[TableLine]) -> list[TableRow]:
    """Rebuild names printed on two lines and only keep rows with an id."""
    rows: list[TableRow] = []
    for i, table_line in enumerate(parsed):
        if table_line.row_id is None:
            continue  # lines without a row_id are halfs of a wrapped name or a heading
        name = table_line.name
        if name == "":
            name = parsed[i - 1].name + " " + parsed[i + 1].name
        rows.append(
            TableRow(row_id=table_line.row_id, name=name, values=table_line.values)
        )
    return rows


if __name__ == "__main__":
    verify_pdf(TALLA_2024_PATH, TALLA_2024_URL, TALLA_2024_SHA256)
    parsed_lines: list[TableLine] = []
    for (page_number, _), words in read_lines(TALLA_2024_PATH):
        columns = ODD_PAGE_COLUMNS if page_number % 2 else EVEN_PAGE_COLUMNS
        parsed_lines.append(parse_line(words, columns))

    rows = join_wrapped_names(parsed_lines)
    print(rows)
