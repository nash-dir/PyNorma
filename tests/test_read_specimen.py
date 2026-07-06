"""Tests for read_specimen — multi-sheet XLSX selection and non-standard delimiters."""
import openpyxl
import pytest

from pynorma.detect.core import read_specimen, guess_delimiter


# ── Multi-sheet XLSX selection ────────────────────────────────────

def _make_workbook(path, sheets):
    """sheets = list of (name, rows); rows = list of lists."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, rows in sheets:
        ws = wb.create_sheet(name)
        for r in rows:
            ws.append(r)
    wb.save(path)


DATA = [["name", "age", "city"], ["Alice", 30, "Seoul"],
        ["Bob", 25, "Busan"], ["Carol", 28, "Daegu"]]


def test_multisheet_skips_empty_cover(tmp_path):
    p = tmp_path / "wb.xlsx"
    _make_workbook(p, [("readme", [["See the data tab"]]), ("data", DATA)])
    grid, meta = read_specimen(p)
    assert meta["sheet"] == "data"
    assert meta["cols"] == 3


def test_multisheet_keeps_first_when_tabular(tmp_path):
    p = tmp_path / "wb.xlsx"
    _make_workbook(p, [("first", DATA), ("second", DATA + DATA)])
    grid, meta = read_specimen(p)
    assert meta["sheet"] == "first"  # first sheet is already a real table


def test_explicit_sheet_by_index(tmp_path):
    p = tmp_path / "wb.xlsx"
    _make_workbook(p, [("readme", [["cover"]]), ("data", DATA)])
    _, meta = read_specimen(p, sheet=0)
    assert meta["sheet"] == "readme"


def test_explicit_sheet_by_name(tmp_path):
    p = tmp_path / "wb.xlsx"
    _make_workbook(p, [("first", DATA), ("second", DATA)])
    _, meta = read_specimen(p, sheet="second")
    assert meta["sheet"] == "second"


# ── Non-standard delimiters ───────────────────────────────────────

def test_double_colon_delimiter(tmp_path):
    p = tmp_path / "dc.csv"
    p.write_text("a::b::c\n1::2::3\n4::5::6\n7::8::9\n", encoding="utf-8")
    grid, meta = read_specimen(p)
    assert meta["delimiter"] == "::"
    assert grid[0] == ["a", "b", "c"]
    assert meta["cols"] == 3


def test_whitespace_aligned_delimiter(tmp_path):
    p = tmp_path / "sp.csv"
    p.write_text(
        "name    age    city\n"
        "Alice   30     Seoul\n"
        "Bob     25     Busan\n"
        "Carol   28     Daegu\n",
        encoding="utf-8",
    )
    grid, meta = read_specimen(p)
    assert meta["cols"] == 3
    assert grid[0] == ["name", "age", "city"]


def test_single_column_with_spaces_not_split(tmp_path):
    # values contain single spaces but the column is genuinely single-valued
    p = tmp_path / "sc.csv"
    p.write_text("City\nNew York\nLos Angeles\nSan Francisco\nSalt Lake City\n",
                 encoding="utf-8")
    _, meta = read_specimen(p)
    assert meta["cols"] == 1  # must NOT be split on the internal spaces


def test_standard_comma_unchanged(tmp_path):
    p = tmp_path / "std.csv"
    p.write_text("a,b,c\n1,2,3\n4,5,6\n", encoding="utf-8")
    grid, meta = read_specimen(p)
    assert meta["delimiter"] == ","
    assert grid[0] == ["a", "b", "c"]
