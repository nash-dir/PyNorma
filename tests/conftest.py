"""Shared pytest fixtures for PyNorma tests."""

import os
import tempfile

import numpy as np
import pandas as pd
import pytest


# ── File path fixtures ────────────────────────────────────────────

@pytest.fixture
def sample_csv_path():
    """Path to a real sample CSV in the examples directory."""
    return os.path.join(
        os.path.dirname(__file__), "..", "examples", "townbusiness1.csv"
    )


@pytest.fixture
def sample_csv_path_2():
    """Path to a second sample CSV for append tests."""
    return os.path.join(
        os.path.dirname(__file__), "..", "examples", "townbusiness2.csv"
    )


@pytest.fixture
def sample_csv_path_3():
    """Path to a third sample CSV for append tests."""
    return os.path.join(
        os.path.dirname(__file__), "..", "examples", "townbusiness3.csv"
    )


@pytest.fixture
def sample_xlsx_path():
    """Path to a real sample XLSX in the examples directory."""
    return os.path.join(
        os.path.dirname(__file__), "..", "examples", "Kor119.xlsx"
    )


@pytest.fixture
def dict_csv_path():
    """Path to the example clarification dictionary."""
    return os.path.join(
        os.path.dirname(__file__), "..", "examples", "townbusiness_dict.csv"
    )


# ── Messy DataFrames ──────────────────────────────────────────────

@pytest.fixture
def messy_df():
    """A DataFrame simulating a messy file with comment rows, blank rows,
    and a data table embedded in the middle."""
    data = [
        [None, None, None, None, None],           # row 0: blank
        ["Report", "Title", None, None, None],     # row 1: comment
        ["Date:", "2024-01-01", None, None, None],  # row 2: comment
        [None, None, None, None, None],            # row 3: blank
        ["Name", "Age", "City", "Score", "Grade"],  # row 4: header
        ["Alice", "25", "Seoul", "88", "A"],        # row 5: data
        ["Bob", "30", "Busan", "72", "B"],          # row 6: data
        ["Carol", "22", "Daegu", "95", "A+"],       # row 7: data
        ["Dave", "28", "Incheon", "60", "C"],       # row 8: data
        [None, None, None, None, None],            # row 9: blank
    ]
    return pd.DataFrame(data)


@pytest.fixture
def messy_df_with_offset():
    """Messy DF where the table is offset to the right (columns 2-6)."""
    data = [
        [None, None, None, None, None, None, None],
        [None, None, "Name", "Age", "City", "Score", None],
        [None, None, "Alice", "25", "Seoul", "88", None],
        [None, None, "Bob", "30", "Busan", "72", None],
        [None, None, "Carol", "22", "Daegu", "95", None],
        [None, None, None, None, None, None, None],
    ]
    return pd.DataFrame(data)


@pytest.fixture
def all_blanks_df():
    """A DataFrame of only blank/None values."""
    return pd.DataFrame([[None, None], [None, None], ["", "  "]])


@pytest.fixture
def single_row_df():
    """A DataFrame with just one row."""
    return pd.DataFrame([["Name", "Age", "City"]])


@pytest.fixture
def numeric_only_df():
    """A DataFrame with numeric data only (no string header)."""
    return pd.DataFrame({
        0: [1, 2, 3, 4, 5],
        1: [10, 20, 30, 40, 50],
        2: [100, 200, 300, 400, 500],
    })


@pytest.fixture
def sparse_df():
    """A DataFrame with many scattered NaN values."""
    data = [
        ["Header1", "Header2", "Header3"],
        ["a", None, "c"],
        [None, "b", None],
        ["d", "e", "f"],
        [None, None, None],
        ["g", None, "i"],
    ]
    return pd.DataFrame(data)


# ── Clean DataFrames ──────────────────────────────────────────────

@pytest.fixture
def clean_df():
    """A simple, clean DataFrame with a proper header."""
    return pd.DataFrame({
        "Name": ["Alice", "Bob", "Carol"],
        "Age": [25, 30, 22],
        "City": ["Seoul", "Busan", "Daegu"],
    })


@pytest.fixture
def large_clean_df():
    """A larger clean DataFrame for performance-sensitive tests."""
    n = 200
    return pd.DataFrame({
        "ID": range(n),
        "Name": [f"Person_{i}" for i in range(n)],
        "Value": np.random.randint(0, 1000, n),
        "Category": np.random.choice(["A", "B", "C", "D"], n),
    })


# ── Preprocessor-specific fixtures ────────────────────────────────

@pytest.fixture
def multi_value_df():
    """A DataFrame with multi-valued cells (for atomizer tests)."""
    return pd.DataFrame({
        "Name": ["Alice", "Bob", "Carol"],
        "Hobbies": ["reading,swimming", "coding,gaming,cooking", "drawing"],
        "Score": [90, 85, 78],
    })


@pytest.fixture
def multi_value_semicolon_df():
    """A DataFrame with semicolon-delimited multi-valued cells."""
    return pd.DataFrame({
        "ID": [1, 2, 3],
        "Tags": ["python;java", "rust;go;c++", "javascript"],
        "Count": [10, 20, 30],
    })


@pytest.fixture
def multi_value_pipe_df():
    """A DataFrame with pipe-delimited multi-valued cells."""
    return pd.DataFrame({
        "Region": ["Seoul", "Busan"],
        "Products": ["phone|tablet|laptop", "phone|tablet"],
        "Revenue": [100, 200],
    })


@pytest.fixture
def wide_table_df():
    """A wide-format DataFrame with multi-level headers (for flattener tests)."""
    data = [
        ["Region", "Category", "2023-Q1", "2023-Q2", "2023-Q3", "2023-Q4"],
        ["Region", "Category", "Sales",   "Sales",   "Sales",   "Sales"],
        ["Seoul",  "Food",     "100",     "120",     "130",     "110"],
        ["Seoul",  "Tech",     "200",     "220",     "240",     "210"],
        ["Busan",  "Food",     "80",      "90",      "100",     "85"],
        ["Busan",  "Tech",     "150",     "160",     "170",     "155"],
    ]
    return pd.DataFrame(data)


@pytest.fixture
def wide_table_3level_df():
    """A wide-format DataFrame with 3-level column headers."""
    data = [
        ["Region", "2023",  "2023",  "2024",  "2024"],
        ["Region", "Q1",    "Q2",    "Q1",    "Q2"],
        ["Region", "Sales", "Sales", "Sales", "Sales"],
        ["Seoul",  "100",   "120",   "130",   "140"],
        ["Busan",  "80",    "90",    "85",    "95"],
    ]
    return pd.DataFrame(data)


@pytest.fixture
def nan_like_df():
    """DataFrame containing various NaN-like placeholder values."""
    return pd.DataFrame({
        "col1": ["N/A", "real_value", "NULL", "--", "good"],
        "col2": ["None", "999", "valid", "Missing", "ok"],
    })


@pytest.fixture
def duplicate_rows_df():
    """DataFrame with duplicate grouping keys for merger tests."""
    return pd.DataFrame({
        "Category": ["A", "A", "A", "B", "B", "C"],
        "SubCat": ["x", "x", "y", "x", "x", "z"],
        "Value1": [10, 20, 30, 40, 50, 60],
        "Value2": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
    })


# ── Temporary file fixtures ──────────────────────────────────────

@pytest.fixture
def tmp_csv(tmp_path, clean_df):
    """Write clean_df to a temp CSV and return the path."""
    path = str(tmp_path / "temp.csv")
    clean_df.to_csv(path, index=False)
    return path


@pytest.fixture
def tmp_csv_no_header(tmp_path, clean_df):
    """Write clean_df to a temp CSV without header."""
    path = str(tmp_path / "temp_noheader.csv")
    clean_df.to_csv(path, index=False, header=False)
    return path


@pytest.fixture
def tmp_xlsx(tmp_path, clean_df):
    """Write clean_df to a temp XLSX and return the path."""
    path = str(tmp_path / "temp.xlsx")
    clean_df.to_excel(path, index=False)
    return path


@pytest.fixture
def tmp_clarify_dict(tmp_path):
    """Create a temporary clarification dictionary CSV."""
    dict_df = pd.DataFrame({
        "target": ["FRUIT_APPLE", "FRUIT_BANANA", "FRUIT_CHERRY"],
        "addno": [1.0, 1.0, 2.0],
        "source1": ["apple", "banana", "cherry"],
        "source2": ["Apple", "Banana", None],
        "source3": ["APPLE", None, None],
    })
    path = str(tmp_path / "clarify_dict.csv")
    dict_df.to_csv(path, index=False)
    return path


# ── V2: Table Detection annotation fixtures ───────────────────────

@pytest.fixture
def df_with_side_annotation():
    """5-column data table + 1 annotation column on the right."""
    data = [
        ["Name",  "Age", "City",    "Score", "Grade", None],
        ["Alice", "25",  "Seoul",   "88",    "A",     "출처: 통계청"],
        ["Bob",   "30",  "Busan",   "72",    "B",     None],
        ["Carol", "22",  "Daegu",   "95",    "A+",    "※ 비고"],
        ["Dave",  "28",  "Incheon", "60",    "C",     None],
        ["Eve",   "35",  "Gwangju", "81",    "B+",    None],
    ]
    return pd.DataFrame(data)


@pytest.fixture
def df_with_footnote():
    """4-column data table + 2 footnote rows at the bottom."""
    data = [
        ["Name",  "Age", "City",  "Score"],
        ["Alice", "25",  "Seoul", "88"],
        ["Bob",   "30",  "Busan", "72"],
        ["Carol", "22",  "Daegu", "95"],
        ["Dave",  "28",  "Incheon", "60"],
        ["※ 본 자료는 2024년 기준입니다.", None, None, None],
        ["출처: 행정안전부",               None, None, None],
    ]
    return pd.DataFrame(data)


@pytest.fixture
def df_with_legend_column():
    """1 legend column on the left + 4-column data table."""
    data = [
        [None,        "Name",  "Age", "City",  "Score"],
        ["범례",      "Alice", "25",  "Seoul", "88"],
        [None,        "Bob",   "30",  "Busan", "72"],
        ["참고사항",  "Carol", "22",  "Daegu", "95"],
        [None,        "Dave",  "28",  "Incheon", "60"],
        [None,        "Eve",   "35",  "Gwangju", "81"],
    ]
    return pd.DataFrame(data)


@pytest.fixture
def df_gradient_edge():
    """DataFrame where density gradually decreases toward the edges."""
    data = [
        [None,  None,  None,    None,   None,   None],
        [None,  "Name","Age",   "City", "Score",None],
        [None,  "A",   "25",   "Seoul", "88",   None],
        [None,  "B",   "30",   "Busan", "72",   None],
        [None,  "C",   "22",   "Daegu", "95",   None],
        [None,  None,  None,    None,   None,   None],
        [None,  None,  None,    None,   None,   None],
    ]
    return pd.DataFrame(data)

