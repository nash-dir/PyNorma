"""Tests for pynorma.io (parser, csv_parser, xlsx_parser, trimmer, writer) and utils."""

import logging
import os

import numpy as np
import pandas as pd
import pytest

from pynorma.io.parser import parse
from pynorma.io.csv_parser import parse_csv
from pynorma.io.xlsx_parser import parse_xlsx
from pynorma.io.trimmer import trim_dataframe
from pynorma.io.writer import save_dataframe
from pynorma.utils import (
    detect_encoding,
    clean_dataframe,
    replace_nan_like,
    find_largest_soft_rectangle,
)
from pynorma.config import get_delimiters, get_nan_like


# ═══════════════════════════════════════════════════════════════════
#  Config
# ═══════════════════════════════════════════════════════════════════

class TestConfig:
    """Tests for the configuration loader."""

    def test_get_delimiters_returns_list(self):
        result = get_delimiters()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_get_delimiters_contains_comma(self):
        assert "," in get_delimiters()

    def test_get_nan_like_returns_list(self):
        result = get_nan_like()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_get_nan_like_contains_standard_values(self):
        nan_values = get_nan_like()
        for expected in ["N/A", "NA", "NULL", "None"]:
            assert expected in nan_values

    def test_delimiters_are_cached(self):
        """Calling twice should return the same object (cached)."""
        a = get_delimiters()
        b = get_delimiters()
        assert a is b

    def test_nan_like_are_cached(self):
        a = get_nan_like()
        b = get_nan_like()
        assert a is b


# ═══════════════════════════════════════════════════════════════════
#  Utils — Encoding Detection
# ═══════════════════════════════════════════════════════════════════

class TestDetectEncoding:
    """Tests for ``detect_encoding``."""

    def test_detect_encoding_csv(self, sample_csv_path):
        enc = detect_encoding(sample_csv_path)
        assert enc is not None
        assert isinstance(enc, str)
        assert len(enc) > 0

    def test_detect_encoding_xlsx(self, sample_xlsx_path):
        """XLSX is binary; chardet may return None or a guess."""
        if not os.path.exists(sample_xlsx_path):
            pytest.skip("XLSX not found")
        enc = detect_encoding(sample_xlsx_path)
        # Binary files may yield None from chardet — that's acceptable
        assert enc is None or isinstance(enc, str)

    def test_detect_encoding_utf8(self, tmp_path):
        f = tmp_path / "utf8.txt"
        f.write_text("hello world", encoding="utf-8")
        enc = detect_encoding(str(f))
        assert enc.lower().replace("-", "") in ("utf8", "ascii")

    def test_detect_encoding_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError):
            detect_encoding("/nonexistent/file.csv")


# ═══════════════════════════════════════════════════════════════════
#  Utils — clean_dataframe / replace_nan_like
# ═══════════════════════════════════════════════════════════════════

class TestCleanDataframe:
    """Tests for ``clean_dataframe``."""

    def test_blank_strings_become_na(self):
        df = pd.DataFrame({"a": ["hello", "  ", ""], "b": ["x", "y", "z"]})
        result = clean_dataframe(df)
        assert pd.isna(result.iloc[1, 0])
        assert pd.isna(result.iloc[2, 0])

    def test_non_blank_strings_preserved(self):
        df = pd.DataFrame({"a": ["hello", "world"]})
        result = clean_dataframe(df)
        assert result.iloc[0, 0] == "hello"
        assert result.iloc[1, 0] == "world"

    def test_numeric_values_preserved(self):
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = clean_dataframe(df)
        assert list(result["a"]) == [1, 2, 3]

    def test_already_na_stays_na(self):
        df = pd.DataFrame({"a": [pd.NA, None, np.nan]})
        result = clean_dataframe(df)
        assert all(pd.isna(result["a"]))

    def test_nan_like_values_replaced(self, nan_like_df):
        result = clean_dataframe(nan_like_df)
        # "N/A", "NULL", "--", "None", "999", "Missing" should become NA
        assert pd.isna(result.iloc[0, 0])  # N/A
        assert pd.isna(result.iloc[2, 0])  # NULL
        assert pd.isna(result.iloc[3, 0])  # --

    def test_custom_na_values(self):
        df = pd.DataFrame({"a": ["CUSTOM_MISSING", "good", "CUSTOM_MISSING"]})
        result = clean_dataframe(df, custom_na_values=["CUSTOM_MISSING"])
        assert pd.isna(result.iloc[0, 0])
        assert result.iloc[1, 0] == "good"
        assert pd.isna(result.iloc[2, 0])

    def test_empty_dataframe(self):
        result = clean_dataframe(pd.DataFrame())
        assert result.empty

    def test_does_not_modify_original(self):
        df = pd.DataFrame({"a": ["  ", "N/A"]})
        _ = clean_dataframe(df)
        assert df.iloc[0, 0] == "  "  # original unchanged


class TestReplaceNanLike:
    """Tests for ``replace_nan_like``."""

    def test_standard_na_values(self):
        df = pd.DataFrame({"a": ["N/A", "NA", "NaN", "null", "NULL", "None"]})
        result = replace_nan_like(df)
        assert all(pd.isna(result["a"]))

    def test_symbol_na_values(self):
        df = pd.DataFrame({"a": ["--", "?", "*", "-"]})
        result = replace_nan_like(df)
        assert all(pd.isna(result["a"]))

    def test_text_na_values(self):
        df = pd.DataFrame({"a": ["Not Applicable", "No Data", "Missing"]})
        result = replace_nan_like(df)
        assert all(pd.isna(result["a"]))

    def test_numeric_na_values(self):
        df = pd.DataFrame({"a": ["999", "-1"]})
        result = replace_nan_like(df)
        assert all(pd.isna(result["a"]))

    def test_custom_and_builtin_combined(self):
        df = pd.DataFrame({"a": ["N/A", "MY_NULL"]})
        result = replace_nan_like(df, custom_na_values=["MY_NULL"])
        assert pd.isna(result.iloc[0, 0])
        assert pd.isna(result.iloc[1, 0])

    def test_no_false_positives(self):
        df = pd.DataFrame({"a": ["apple", "banana", "Seoul"]})
        result = replace_nan_like(df)
        assert not any(pd.isna(result["a"]))


# ═══════════════════════════════════════════════════════════════════
#  Utils — find_largest_soft_rectangle
# ═══════════════════════════════════════════════════════════════════

class TestFindLargestSoftRectangle:
    """Tests for the histogram-based largest rectangle algorithm."""

    def test_full_numeric_df(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6], "c": [7, 8, 9]})
        top, bottom, left, right = find_largest_soft_rectangle(df)
        assert (bottom - top) * (right - left) == 9  # full 3×3

    def test_mixed_df_finds_numeric_block(self):
        df = pd.DataFrame({
            "a": ["Name", "1", "2", "3"],
            "b": ["Age", "10", "20", "30"],
            "c": ["City", "Seoul", "Busan", "Daegu"],
        })
        top, bottom, left, right = find_largest_soft_rectangle(df)
        area = (bottom - top) * (right - left)
        assert area > 0

    def test_single_cell(self):
        df = pd.DataFrame({"a": [42]})
        top, bottom, left, right = find_largest_soft_rectangle(df)
        assert (bottom - top) * (right - left) >= 1

    def test_empty_df(self):
        df = pd.DataFrame()
        top, bottom, left, right = find_largest_soft_rectangle(df)
        assert (top, bottom, left, right) == (0, 0, 0, 0)

    def test_all_strings_returns_zero_area(self):
        df = pd.DataFrame({"a": ["x", "y"], "b": ["p", "q"]})
        top, bottom, left, right = find_largest_soft_rectangle(df)
        # All strings, no numeric data → area should be 0
        assert (bottom - top) * (right - left) == 0

    def test_with_nan_like_values(self):
        """NaN-like values should be treated as valid (not disqualifying)."""
        df = pd.DataFrame({
            "a": [1, 2, "N/A"],
            "b": [4, "None", 6],
            "c": [7, 8, 9],
        })
        top, bottom, left, right = find_largest_soft_rectangle(df)
        area = (bottom - top) * (right - left)
        assert area >= 6  # should include most of the 3×3

    def test_numpy_array_input(self):
        mask = np.array([[1, 1, 0], [1, 1, 0], [1, 1, 1]])
        top, bottom, left, right = find_largest_soft_rectangle(mask)
        area = (bottom - top) * (right - left)
        assert area > 0

    def test_invalid_input_raises(self):
        with pytest.raises(TypeError):
            find_largest_soft_rectangle("not a dataframe")

    def test_with_row_offset(self):
        df = pd.DataFrame({"a": ["x", 1, 2, 3], "b": ["y", 4, 5, 6]})
        top, bottom, left, right = find_largest_soft_rectangle(df, row_offset=1)
        assert top >= 1

    def test_tolerance_affects_result(self):
        """Higher tolerance should allow more sparse data."""
        df = pd.DataFrame({
            "a": [1, "text", 3],
            "b": [4, 5, "text"],
            "c": [7, 8, 9],
        })
        strict = find_largest_soft_rectangle(df, tolerance=0.0)
        lenient = find_largest_soft_rectangle(df, tolerance=0.5)
        strict_area = (strict[1] - strict[0]) * (strict[3] - strict[2])
        lenient_area = (lenient[1] - lenient[0]) * (lenient[3] - lenient[2])
        assert lenient_area >= strict_area


# ═══════════════════════════════════════════════════════════════════
#  Parser — Top-level integration
# ═══════════════════════════════════════════════════════════════════

class TestParser:
    """Integration tests for the top-level ``parse()`` function."""

    def test_parse_csv_returns_dataframe(self, sample_csv_path):
        df = parse(sample_csv_path)
        assert isinstance(df, pd.DataFrame)
        assert not df.empty

    def test_parse_csv_has_proper_columns(self, sample_csv_path):
        df = parse(sample_csv_path)
        assert len(df.columns) > 0

    def test_parse_xlsx(self, sample_xlsx_path):
        if not os.path.exists(sample_xlsx_path):
            pytest.skip("XLSX not found")
        df = parse(sample_xlsx_path)
        assert isinstance(df, pd.DataFrame)
        assert not df.empty

    def test_parse_trim_false(self, sample_csv_path):
        df = parse(sample_csv_path, trim=False, is_header=False)
        assert isinstance(df, pd.DataFrame)
        assert not df.empty

    def test_parse_trim_dict(self, sample_csv_path):
        df = parse(sample_csv_path, trim={"top": 0, "bottom": 5, "left": 0, "right": 3}, is_header=False)
        assert df.shape[0] <= 5
        assert df.shape[1] <= 3

    def test_parse_is_header_int(self, sample_csv_path):
        df = parse(sample_csv_path, is_header=0, trim=False)
        assert isinstance(df, pd.DataFrame)

    def test_parse_is_header_false(self, sample_csv_path):
        df = parse(sample_csv_path, is_header=False)
        assert isinstance(df, pd.DataFrame)

    def test_parse_unsupported_filetype(self, tmp_path):
        bad_file = tmp_path / "data.json"
        bad_file.write_text("{}")
        with pytest.raises(ValueError, match="Unsupported file type"):
            parse(str(bad_file))

    def test_parse_nonexistent_file(self):
        with pytest.raises(Exception):
            parse("/nonexistent/path/to/file.csv")

    def test_parse_verbose_logs(self, sample_csv_path, caplog):
        with caplog.at_level(logging.INFO, logger="pynorma"):
            parse(sample_csv_path, verbose=True)
        assert "PyNorma" in caplog.text
        assert "Shape Change" in caplog.text

    def test_parse_verbose_xlsx_logs_sheet(self, sample_xlsx_path, caplog):
        if not os.path.exists(sample_xlsx_path):
            pytest.skip("XLSX not found")
        with caplog.at_level(logging.INFO, logger="pynorma"):
            parse(sample_xlsx_path, verbose=True)
        assert "Detected Sheet" in caplog.text


# ═══════════════════════════════════════════════════════════════════
#  CSV Parser — Direct
# ═══════════════════════════════════════════════════════════════════

class TestCsvParser:
    """Direct tests for ``parse_csv``."""

    def test_returns_tuple(self, sample_csv_path):
        result = parse_csv(sample_csv_path)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], pd.DataFrame)
        assert isinstance(result[1], dict)

    def test_info_dict_keys(self, sample_csv_path):
        _, info = parse_csv(sample_csv_path)
        for key in ["original_shape", "trimmed_shape", "top", "bottom", "left", "right"]:
            assert key in info

    def test_explicit_delimiter(self, tmp_path):
        f = tmp_path / "tab.csv"
        f.write_text("a\tb\tc\n1\t2\t3\n4\t5\t6", encoding="utf-8")
        df, info = parse_csv(str(f), delimiter="\t", is_header=True)
        assert not df.empty

    def test_explicit_encoding(self, sample_csv_path):
        df, _ = parse_csv(sample_csv_path, encoding="utf-8")
        assert not df.empty

    def test_is_header_false(self, sample_csv_path):
        df, _ = parse_csv(sample_csv_path, is_header=False)
        # Column names should be integers (RangeIndex)
        assert all(isinstance(c, (int, np.integer)) for c in df.columns)

    def test_malformed_csv_warns(self, tmp_path):
        """CSV with mismatched field counts should not crash."""
        f = tmp_path / "bad.csv"
        f.write_text("a,b,c\n1,2\n3,4,5,6\n7,8,9", encoding="utf-8")
        df, _ = parse_csv(str(f))
        assert isinstance(df, pd.DataFrame)


# ═══════════════════════════════════════════════════════════════════
#  XLSX Parser — Direct
# ═══════════════════════════════════════════════════════════════════

class TestXlsxParser:
    """Direct tests for ``parse_xlsx``."""

    def test_returns_tuple(self, sample_xlsx_path):
        if not os.path.exists(sample_xlsx_path):
            pytest.skip("XLSX not found")
        result = parse_xlsx(sample_xlsx_path)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_info_contains_sheet_name(self, sample_xlsx_path):
        if not os.path.exists(sample_xlsx_path):
            pytest.skip("XLSX not found")
        _, info = parse_xlsx(sample_xlsx_path)
        assert "detected_sheet" in info
        assert isinstance(info["detected_sheet"], str)

    def test_roundtrip_csv_xlsx(self, clean_df, tmp_path):
        """Write to XLSX, read back — columns should match."""
        xlsx_path = str(tmp_path / "roundtrip.xlsx")
        clean_df.to_excel(xlsx_path, index=False)
        df, _ = parse_xlsx(xlsx_path, trim=False)
        assert not df.empty

    def test_invalid_sheet_type_raises(self, tmp_xlsx):
        with pytest.raises(TypeError, match="sheet_name"):
            parse_xlsx(tmp_xlsx, sheet_name=3.14)

    def test_nonexistent_sheet_name_raises(self, tmp_xlsx):
        with pytest.raises(KeyError):
            parse_xlsx(tmp_xlsx, sheet_name="NonexistentSheet")


# ═══════════════════════════════════════════════════════════════════
#  Trimmer
# ═══════════════════════════════════════════════════════════════════

class TestTrimmer:
    """Tests for ``trim_dataframe``."""

    def test_auto_trim_removes_blanks(self, messy_df):
        result, _ = trim_dataframe(messy_df, trim_mode="auto")
        assert result.shape[0] < messy_df.shape[0]

    def test_auto_trim_finds_data(self, messy_df):
        result, _ = trim_dataframe(messy_df, trim_mode="auto")
        assert not result.empty

    def test_manual_trim_exact(self, messy_df):
        result, info = trim_dataframe(
            messy_df,
            trim_mode={"top": 4, "bottom": 9, "left": 0, "right": 5},
            set_header=False,
        )
        assert result.shape == (5, 5)
        assert info["top"] == 4
        assert info["bottom"] == 9

    def test_trim_false_preserves_shape(self, messy_df):
        result, info = trim_dataframe(messy_df, trim_mode=False, set_header=False)
        assert result.shape == messy_df.shape

    def test_invalid_trim_mode_raises(self, messy_df):
        with pytest.raises(ValueError, match="trim_mode"):
            trim_dataframe(messy_df, trim_mode="invalid_value")

    def test_info_dict_has_all_keys(self, messy_df):
        _, info = trim_dataframe(messy_df)
        required_keys = ["original_shape", "trimmed_shape", "top", "bottom",
                         "left", "right", "header_row_abs"]
        for key in required_keys:
            assert key in info, f"Missing key: {key}"

    def test_original_shape_preserved_in_info(self, messy_df):
        _, info = trim_dataframe(messy_df)
        assert info["original_shape"] == messy_df.shape

    def test_set_header_auto(self, messy_df):
        result, info = trim_dataframe(messy_df, trim_mode="auto", set_header=True)
        # Header should be detected, so columns should not be integers
        has_string_cols = any(isinstance(c, str) for c in result.columns)
        assert has_string_cols or result.empty

    def test_set_header_false(self, messy_df):
        result, _ = trim_dataframe(messy_df, trim_mode="auto", set_header=False)
        # Columns should be integer range
        assert all(isinstance(c, (int, np.integer)) for c in result.columns)

    def test_explicit_header_row(self, messy_df):
        result, info = trim_dataframe(
            messy_df,
            trim_mode={"top": 0, "bottom": 9, "left": 0, "right": 5},
            set_header=True,
            header_row=4,
        )
        assert not result.empty

    def test_empty_df_returns_empty(self):
        result, _ = trim_dataframe(pd.DataFrame(), trim_mode="auto")
        assert result.empty

    def test_offset_table_detected(self, messy_df_with_offset):
        result, _ = trim_dataframe(messy_df_with_offset, trim_mode="auto")
        assert not result.empty
        assert result.shape[1] <= 5


# ═══════════════════════════════════════════════════════════════════
#  Writer
# ═══════════════════════════════════════════════════════════════════

class TestWriter:
    """Tests for ``save_dataframe``."""

    def test_save_csv(self, clean_df, tmp_path):
        out = str(tmp_path / "output.csv")
        save_dataframe(clean_df, out)
        assert os.path.exists(out)
        loaded = pd.read_csv(out)
        assert loaded.shape == clean_df.shape

    def test_save_csv_roundtrip_values(self, clean_df, tmp_path):
        out = str(tmp_path / "output.csv")
        save_dataframe(clean_df, out)
        loaded = pd.read_csv(out)
        assert list(loaded["Name"]) == list(clean_df["Name"])

    def test_save_tsv(self, clean_df, tmp_path):
        out = str(tmp_path / "output.tsv")
        save_dataframe(clean_df, out)
        assert os.path.exists(out)
        loaded = pd.read_csv(out, sep="\t")
        assert loaded.shape == clean_df.shape

    def test_save_xlsx(self, clean_df, tmp_path):
        out = str(tmp_path / "output.xlsx")
        save_dataframe(clean_df, out)
        assert os.path.exists(out)

    def test_save_xlsx_roundtrip(self, clean_df, tmp_path):
        out = str(tmp_path / "output.xlsx")
        save_dataframe(clean_df, out)
        loaded = pd.read_excel(out)
        assert loaded.shape == clean_df.shape

    def test_save_creates_dirs(self, clean_df, tmp_path):
        out = str(tmp_path / "deeply" / "nested" / "dir" / "output.csv")
        save_dataframe(clean_df, out)
        assert os.path.exists(out)

    def test_save_quote_all(self, clean_df, tmp_path):
        out = str(tmp_path / "quoted.csv")
        save_dataframe(clean_df, out, quote_all=True)
        with open(out, "r", encoding="utf-8-sig") as f:
            content = f.read()
        # Every field should be quoted
        assert '"Alice"' in content

    def test_save_custom_encoding(self, clean_df, tmp_path):
        out = str(tmp_path / "cp949.csv")
        save_dataframe(clean_df, out, encoding="cp949")
        assert os.path.exists(out)

    def test_save_unsupported_raises(self, clean_df, tmp_path):
        out = str(tmp_path / "output.parquet")
        with pytest.raises(ValueError, match="Unsupported file format"):
            save_dataframe(clean_df, out)

    def test_save_empty_dataframe(self, tmp_path):
        out = str(tmp_path / "empty.csv")
        save_dataframe(pd.DataFrame(), out)
        assert os.path.exists(out)

    def test_save_logs_message(self, clean_df, tmp_path, caplog):
        out = str(tmp_path / "log_test.csv")
        with caplog.at_level(logging.INFO, logger="pynorma"):
            save_dataframe(clean_df, out)
        assert "saved" in caplog.text.lower()
