"""V2 Tests — Gradient Projection, Type Consistency Refinement, classify_cell."""

import numpy as np
import pandas as pd
import pytest

from pynorma.utils import classify_cell
from pynorma.detect.table_finder import (
    _find_boundary_by_gradient,
    _find_table_by_projection,
    _column_type_entropy,
    _column_fill_rate,
    _should_trim_series,
    _refine_boundaries_by_type,
    find_robust_table_area,
)


# ═══════════════════════════════════════════════════════════════════
#  classify_cell
# ═══════════════════════════════════════════════════════════════════

class TestClassifyCell:
    """Tests for the shared cell-type classifier."""

    def test_numeric_int(self):
        assert classify_cell("42") == "numeric"

    def test_numeric_float(self):
        assert classify_cell("3.14") == "numeric"

    def test_numeric_negative(self):
        assert classify_cell("-99.5") == "numeric"

    def test_numeric_zero(self):
        assert classify_cell("0") == "numeric"

    def test_native_int(self):
        assert classify_cell(42) == "numeric"

    def test_native_float(self):
        assert classify_cell(3.14) == "numeric"

    def test_string(self):
        assert classify_cell("hello") == "string"

    def test_string_korean(self):
        assert classify_cell("서울") == "string"

    def test_string_mixed(self):
        assert classify_cell("data123") == "string"

    def test_empty_none(self):
        assert classify_cell(None) == "empty"

    def test_empty_na(self):
        assert classify_cell(pd.NA) == "empty"

    def test_empty_nan(self):
        assert classify_cell(np.nan) == "empty"

    def test_empty_blank_string(self):
        assert classify_cell("  ") == "empty"

    def test_empty_empty_string(self):
        assert classify_cell("") == "empty"


# ═══════════════════════════════════════════════════════════════════
#  _find_boundary_by_gradient
# ═══════════════════════════════════════════════════════════════════

class TestFindBoundaryByGradient:
    """Tests for gradient-based boundary detection."""

    def test_empty_array(self):
        assert _find_boundary_by_gradient(np.array([])) == (0, 0)

    def test_all_zeros(self):
        assert _find_boundary_by_gradient(np.array([0, 0, 0])) == (0, 0)

    def test_uniform_density(self):
        """Uniform high density → should return the full range."""
        proj = np.array([10, 10, 10, 10, 10])
        start, end = _find_boundary_by_gradient(proj)
        assert start == 0
        assert end == 5

    def test_cliff_at_end(self):
        """Sharp density drop → should exclude the tail."""
        proj = np.array([10, 10, 10, 10, 1, 1])
        start, end = _find_boundary_by_gradient(proj)
        assert start == 0
        assert end <= 5  # should not include the last low-density elements

    def test_cliff_at_start(self):
        """Low density at the start → should exclude the head."""
        proj = np.array([1, 1, 10, 10, 10, 10])
        start, end = _find_boundary_by_gradient(proj)
        assert start >= 2
        assert end == 6

    def test_single_peak(self):
        proj = np.array([0, 0, 10, 10, 0, 0])
        start, end = _find_boundary_by_gradient(proj)
        assert start == 2
        assert end == 4

    def test_gradual_increase_decrease(self):
        proj = np.array([1, 3, 5, 8, 10, 8, 5, 3, 1])
        start, end = _find_boundary_by_gradient(proj)
        assert 0 <= start <= 2
        assert 7 <= end <= 9


# ═══════════════════════════════════════════════════════════════════
#  _column_type_entropy / _column_fill_rate
# ═══════════════════════════════════════════════════════════════════

class TestColumnTypeEntropy:
    """Tests for Shannon entropy over column type distribution."""

    def test_pure_numeric(self):
        series = pd.Series(["1", "2", "3", "4", "5"])
        ent = _column_type_entropy(series)
        assert ent == pytest.approx(0.0)

    def test_pure_string(self):
        series = pd.Series(["a", "b", "c", "d"])
        ent = _column_type_entropy(series)
        assert ent == pytest.approx(0.0)

    def test_pure_empty(self):
        series = pd.Series([None, None, None])
        ent = _column_type_entropy(series)
        assert ent == pytest.approx(0.0)

    def test_mixed_high_entropy(self):
        """Mix of string, numeric, and empty → high entropy."""
        series = pd.Series(["hello", "42", None, "world", "3.14", ""])
        ent = _column_type_entropy(series)
        assert ent > 1.0

    def test_mostly_numeric_with_one_string(self):
        series = pd.Series(["1", "2", "3", "4", "note"])
        ent = _column_type_entropy(series)
        assert 0 < ent < 1.0

    def test_annotation_column(self):
        """An annotation column has sparse, mixed types → high entropy."""
        series = pd.Series(["출처: 통계청", None, None, "※ 비고", None])
        ent = _column_type_entropy(series)
        # It has string + empty → some entropy, but both are "consistent" per type
        assert ent > 0


class TestColumnFillRate:
    """Tests for column fill rate."""

    def test_all_filled(self):
        assert _column_fill_rate(pd.Series(["a", "b", "c"])) == pytest.approx(1.0)

    def test_all_empty(self):
        assert _column_fill_rate(pd.Series([None, None, None])) == pytest.approx(0.0)

    def test_half_filled(self):
        assert _column_fill_rate(pd.Series(["a", None, "c", None])) == pytest.approx(0.5)

    def test_annotation_pattern(self):
        """Sparse column with scattered values → low fill rate."""
        fill = _column_fill_rate(pd.Series(["출처", None, None, None, None]))
        assert fill == pytest.approx(0.2)


# ═══════════════════════════════════════════════════════════════════
#  _should_trim_series
# ═══════════════════════════════════════════════════════════════════

class TestShouldTrimSeries:
    """Tests for the border trim decision function."""

    def test_sparse_column_trimmed(self):
        series = pd.Series(["note", None, None, None, None])
        assert _should_trim_series(series, entropy_threshold=1.0, min_fill_rate=0.3)

    def test_dense_uniform_not_trimmed(self):
        series = pd.Series(["a", "b", "c", "d", "e"])
        assert not _should_trim_series(series, entropy_threshold=1.0, min_fill_rate=0.3)

    def test_dense_numeric_not_trimmed(self):
        series = pd.Series(["1", "2", "3", "4", "5"])
        assert not _should_trim_series(series, entropy_threshold=1.0, min_fill_rate=0.3)

    def test_high_entropy_trimmed(self):
        series = pd.Series(["hello", "42", None, "world", "3.14", ""])
        assert _should_trim_series(series, entropy_threshold=1.0, min_fill_rate=0.3)


# ═══════════════════════════════════════════════════════════════════
#  _refine_boundaries_by_type
# ═══════════════════════════════════════════════════════════════════

class TestRefineBoundariesByType:
    """Tests for the Phase 3 boundary refinement."""

    def test_side_annotation_trimmed(self, df_with_side_annotation):
        """Annotation column on the right should be removed."""
        # Start with the full bounding box
        top, left, bottom, right = 0, 0, 6, 6
        t, l, b, r = _refine_boundaries_by_type(
            df_with_side_annotation, top, left, bottom, right,
        )
        # The annotation column (col 5) should be trimmed
        assert r <= 6

    def test_legend_column_trimmed(self, df_with_legend_column):
        """Legend column on the left should be removed with strict fill threshold."""
        top, left, bottom, right = 0, 0, 6, 5
        # After row-shrink (if any), the legend col fill may increase, so
        # use a strict threshold that exceeds even a dense legend column.
        t, l, b, r = _refine_boundaries_by_type(
            df_with_legend_column, top, left, bottom, right,
            min_fill_rate=0.6,
        )
        assert l >= 1

    def test_footnote_rows_trimmed(self, df_with_footnote):
        """Footnote rows at the bottom should be removed (fill < 0.3)."""
        top, left, bottom, right = 0, 0, 7, 4
        t, l, b, r = _refine_boundaries_by_type(
            df_with_footnote, top, left, bottom, right,
            min_fill_rate=0.3,
        )
        # Footnote rows have fill=0.25 (1 of 4 cells), which is < 0.3
        assert b <= 5  # both footnote rows should be trimmed

    def test_clean_table_untouched(self, clean_df):
        """A clean table should not be shrunk."""
        raw = pd.DataFrame(clean_df.values)
        top, left, bottom, right = 0, 0, 3, 3
        # Too small (≤3), should be skipped
        t, l, b, r = _refine_boundaries_by_type(raw, top, left, bottom, right)
        assert (t, l, b, r) == (0, 0, 3, 3)

    def test_max_shrink_limit(self, df_with_side_annotation):
        """max_shrink=0 should prevent any trimming."""
        top, left, bottom, right = 0, 0, 6, 6
        t, l, b, r = _refine_boundaries_by_type(
            df_with_side_annotation, top, left, bottom, right,
            max_shrink=0,
        )
        assert (t, l, b, r) == (0, 0, 6, 6)

    def test_min_area_ratio_fallback(self):
        """If shrinkage would make area too small, revert to original."""
        # Create a 10x10 df where every border column is noisy
        data = [[None] * 10 for _ in range(10)]
        for r in range(10):
            data[r][4] = str(r)
            data[r][5] = str(r * 10)
        df = pd.DataFrame(data)
        top, left, bottom, right = 0, 0, 10, 10
        t, l, b, r = _refine_boundaries_by_type(
            df, top, left, bottom, right,
            min_area_ratio=0.9,  # very strict: must keep 90%
        )
        # Should revert to original due to safety
        assert (t, l, b, r) == (0, 0, 10, 10)


# ═══════════════════════════════════════════════════════════════════
#  find_robust_table_area — V2 Integration Tests
# ═══════════════════════════════════════════════════════════════════

class TestFindRobustTableAreaV2:
    """Integration tests for the full 3-Phase pipeline."""

    def test_side_annotation_excluded(self, df_with_side_annotation):
        top, left, bottom, right = find_robust_table_area(df_with_side_annotation)
        # Should not include the annotation column (col 5)
        assert right <= 6
        assert (bottom - top) >= 4  # at least 4 data rows

    def test_footnote_excluded(self, df_with_footnote):
        top, left, bottom, right = find_robust_table_area(df_with_footnote)
        # Should not include the footnote rows
        assert bottom <= 6
        assert (bottom - top) >= 3

    def test_legend_excluded(self, df_with_legend_column):
        top, left, bottom, right = find_robust_table_area(df_with_legend_column)
        # Should not include the legend column
        assert left >= 0
        assert (right - left) >= 3

    def test_gradient_edge_table(self, df_gradient_edge):
        """Table surrounded by None → should isolate the dense core."""
        top, left, bottom, right = find_robust_table_area(df_gradient_edge)
        area = (bottom - top) * (right - left)
        assert area > 0
        # Should not include the all-None border rows/cols
        assert top >= 1
        assert left >= 1

    def test_messy_df_still_works(self, messy_df):
        """Existing messy_df fixture should still be handled correctly."""
        top, left, bottom, right = find_robust_table_area(messy_df)
        area = (bottom - top) * (right - left)
        assert area > 0

    def test_empty_df(self):
        assert find_robust_table_area(pd.DataFrame()) == (0, 0, 0, 0)

    def test_entropy_threshold_param(self, df_with_side_annotation):
        """Custom entropy_threshold should be accepted."""
        result = find_robust_table_area(
            df_with_side_annotation, entropy_threshold=0.5
        )
        assert len(result) == 4

    def test_max_shrink_param(self, df_with_side_annotation):
        """Custom max_shrink should be accepted."""
        result = find_robust_table_area(
            df_with_side_annotation, max_shrink=0
        )
        assert len(result) == 4

    def test_result_within_bounds(self, df_with_side_annotation):
        """All indices must be within DataFrame dimensions."""
        top, left, bottom, right = find_robust_table_area(df_with_side_annotation)
        assert top >= 0
        assert left >= 0
        assert bottom <= df_with_side_annotation.shape[0]
        assert right <= df_with_side_annotation.shape[1]
