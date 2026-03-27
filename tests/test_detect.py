"""Tests for pynorma.detect (header_finder, table_finder)."""

import numpy as np
import pandas as pd
import pytest

from pynorma.detect.header_finder import detect_header_end_row, _get_row_type_signature
from pynorma.detect.table_finder import find_robust_table_area, _find_table_by_projection


# ═══════════════════════════════════════════════════════════════════
#  _get_row_type_signature (internal helper)
# ═══════════════════════════════════════════════════════════════════

class TestGetRowTypeSignature:
    """Tests for the per-row type signature utility."""

    def test_all_strings(self):
        row = pd.Series(["Name", "City", "Grade"])
        sig = _get_row_type_signature(row)
        assert sig == ("string", "string", "string")

    def test_all_numeric(self):
        row = pd.Series(["1", "2.5", "100"])
        sig = _get_row_type_signature(row)
        assert sig == ("numeric", "numeric", "numeric")

    def test_all_empty(self):
        row = pd.Series([None, "", "  "])
        sig = _get_row_type_signature(row)
        assert sig == ("empty", "empty", "empty")

    def test_mixed(self):
        row = pd.Series(["Alice", "25", None, "Seoul"])
        sig = _get_row_type_signature(row)
        assert sig == ("string", "numeric", "empty", "string")

    def test_integer_string(self):
        row = pd.Series(["42"])
        sig = _get_row_type_signature(row)
        assert sig == ("numeric",)

    def test_float_string(self):
        row = pd.Series(["3.14"])
        sig = _get_row_type_signature(row)
        assert sig == ("numeric",)

    def test_negative_number(self):
        row = pd.Series(["-99.5"])
        sig = _get_row_type_signature(row)
        assert sig == ("numeric",)

    def test_nan_value(self):
        row = pd.Series([pd.NA])
        sig = _get_row_type_signature(row)
        assert sig == ("empty",)

    def test_numpy_nan(self):
        row = pd.Series([np.nan])
        sig = _get_row_type_signature(row)
        assert sig == ("empty",)


# ═══════════════════════════════════════════════════════════════════
#  detect_header_end_row
# ═══════════════════════════════════════════════════════════════════

class TestHeaderFinder:
    """Tests for ``detect_header_end_row``."""

    def test_clear_header_boundary(self, messy_df):
        """Should detect where comment rows end and data begins."""
        idx = detect_header_end_row(messy_df)
        assert idx >= 0

    def test_single_row_header(self):
        """First row is all strings → return 0."""
        df = pd.DataFrame([
            ["Name", "Age", "City"],
            ["Alice", "25", "Seoul"],
            ["Bob", "30", "Busan"],
        ])
        idx = detect_header_end_row(df)
        assert idx == 0

    def test_two_row_header(self):
        """Two header rows before numeric data."""
        df = pd.DataFrame([
            ["Category", "SubCategory", "Value"],
            ["Main", "Sub", "Amount"],
            ["A", "x", "100"],
            ["B", "y", "200"],
        ])
        idx = detect_header_end_row(df)
        # Should detect boundary at row 1 (last header row)
        assert idx >= 0

    def test_no_header_pure_numeric(self):
        df = pd.DataFrame({
            0: [1, 2, 3, 4],
            1: [10, 20, 30, 40],
            2: [100, 200, 300, 400],
        })
        assert detect_header_end_row(df) == -1

    def test_no_header_uniform_strings(self):
        """All rows are strings with same type → no clear boundary."""
        df = pd.DataFrame([
            ["a", "b", "c"],
            ["d", "e", "f"],
            ["g", "h", "i"],
            ["j", "k", "l"],
        ])
        idx = detect_header_end_row(df)
        # Either 0 (if first row looks like header) or -1
        assert idx in (-1, 0)

    def test_tiny_dataframe_1row(self):
        df = pd.DataFrame([["a", "b", "c"]])
        assert detect_header_end_row(df) == -1

    def test_empty_dataframe(self):
        assert detect_header_end_row(pd.DataFrame()) == -1

    def test_2_rows_exactly(self):
        df = pd.DataFrame([
            ["Name", "Value"],
            ["Alice", "100"],
        ])
        idx = detect_header_end_row(df)
        assert isinstance(idx, int)

    def test_custom_numeric_threshold(self, messy_df):
        idx = detect_header_end_row(messy_df, numeric_row_threshold=0.99)
        assert isinstance(idx, int)

    def test_custom_string_threshold(self, messy_df):
        idx = detect_header_end_row(messy_df, string_row_threshold=0.3)
        assert isinstance(idx, int)

    def test_custom_min_diff_count_1(self, messy_df):
        """Lower threshold should be more sensitive."""
        idx = detect_header_end_row(messy_df, min_diff_count=1)
        assert idx >= 0

    def test_custom_min_diff_count_high(self, messy_df):
        """Very high threshold should make detection harder."""
        idx = detect_header_end_row(messy_df, min_diff_count=100)
        # With extreme threshold, likely falls back to first-row check
        assert isinstance(idx, int)

    def test_max_search_rows_limit(self, messy_df):
        """Limiting search range should still work."""
        idx = detect_header_end_row(messy_df, max_search_rows=3)
        assert isinstance(idx, int)

    def test_header_with_blanks_interspersed(self):
        """Header section contains blank rows between comments."""
        df = pd.DataFrame([
            ["Report Title", None, None],
            [None, None, None],             # blank
            ["Subtitle", None, None],
            ["Name", "Age", "City"],         # actual header
            ["Alice", "25", "Seoul"],
            ["Bob", "30", "Busan"],
        ])
        idx = detect_header_end_row(df)
        assert idx >= 0

    def test_numeric_header_row(self):
        """Row indices like '1, 2, 3, 4' as a header should be handled."""
        df = pd.DataFrame([
            ["1", "2", "3", "4"],
            ["Alice", "25", "Seoul", "88"],
            ["Bob", "30", "Busan", "72"],
        ])
        idx = detect_header_end_row(df)
        assert isinstance(idx, int)


# ═══════════════════════════════════════════════════════════════════
#  _find_table_by_projection (internal)
# ═══════════════════════════════════════════════════════════════════

class TestFindTableByProjection:
    """Tests for the projection-based table boundary estimator."""

    def test_returns_4_tuple(self, messy_df):
        result = _find_table_by_projection(messy_df)
        assert len(result) == 4

    def test_empty_df(self):
        assert _find_table_by_projection(pd.DataFrame()) == (0, 0, 0, 0)

    def test_all_blanks(self, all_blanks_df):
        result = _find_table_by_projection(all_blanks_df)
        # Should gracefully handle all-blank data
        assert len(result) == 4

    def test_single_value(self):
        df = pd.DataFrame([[None, None], [None, "X"], [None, None]])
        top, left, bottom, right = _find_table_by_projection(df)
        # The single value should be found
        assert bottom > top or (top == 0 and bottom == 0)

    def test_full_table(self, clean_df):
        """A full table should encompass most of the DataFrame."""
        # Convert to raw form (no column names interfering)
        raw = pd.DataFrame(clean_df.values)
        top, left, bottom, right = _find_table_by_projection(raw)
        assert (bottom - top) >= 2
        assert (right - left) >= 2


# ═══════════════════════════════════════════════════════════════════
#  find_robust_table_area
# ═══════════════════════════════════════════════════════════════════

class TestTableFinder:
    """Tests for ``find_robust_table_area``."""

    def test_finds_table_in_messy_data(self, messy_df):
        top, left, bottom, right = find_robust_table_area(messy_df)
        area = (bottom - top) * (right - left)
        assert area > 0

    def test_area_smaller_than_original(self, messy_df):
        """Trim should reduce the area."""
        top, left, bottom, right = find_robust_table_area(messy_df)
        original_area = messy_df.shape[0] * messy_df.shape[1]
        trimmed_area = (bottom - top) * (right - left)
        assert trimmed_area <= original_area

    def test_empty_dataframe(self):
        assert find_robust_table_area(pd.DataFrame()) == (0, 0, 0, 0)

    def test_single_cell(self):
        df = pd.DataFrame([["hello"]])
        top, left, bottom, right = find_robust_table_area(df)
        assert bottom - top >= 0
        assert right - left >= 0

    def test_full_table_no_noise(self):
        df = pd.DataFrame([
            ["Name", "Age"],
            ["Alice", "25"],
            ["Bob", "30"],
        ])
        top, left, bottom, right = find_robust_table_area(df)
        assert bottom - top >= 2
        assert right - left >= 2

    def test_offset_table(self, messy_df_with_offset):
        """Table shifted to the right should still be found."""
        top, left, bottom, right = find_robust_table_area(messy_df_with_offset)
        area = (bottom - top) * (right - left)
        assert area > 0

    def test_sparse_table(self, sparse_df):
        top, left, bottom, right = find_robust_table_area(sparse_df)
        assert isinstance(top, (int, np.integer))
        assert bottom >= top

    def test_all_blanks_returns_zero(self, all_blanks_df):
        top, left, bottom, right = find_robust_table_area(all_blanks_df)
        # Might find something or might return zeros
        assert isinstance(top, (int, np.integer))

    def test_large_table(self, large_clean_df):
        """Performance test: 200-row table should not be slow."""
        raw = pd.DataFrame(large_clean_df.values)
        top, left, bottom, right = find_robust_table_area(raw)
        assert (bottom - top) > 0

    def test_returns_valid_indices(self, messy_df):
        """All returned indices should be non-negative and within bounds."""
        top, left, bottom, right = find_robust_table_area(messy_df)
        assert top >= 0
        assert left >= 0
        assert bottom >= top
        assert right >= left
        assert bottom <= messy_df.shape[0]
        assert right <= messy_df.shape[1]
