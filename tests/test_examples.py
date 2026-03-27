"""Ground-truth tests that validate table detection against real example files.

Each example file has a ground-truth definition in ``expected/ground_truth.json``
specifying the expected boundary ranges, minimum data dimensions, and "poison
strings" (text that should NOT appear in the extracted table area).

These tests form the **regression guard** for the detection pipeline:
any algorithm change that breaks a ground truth is immediately visible.
"""

import json
import os
from pathlib import Path

import pandas as pd
import pytest

from pynorma.detect.table_finder import find_robust_table_area, find_robust_table_area_xlsx
from pynorma.detect.border_detector import detect_bordered_area


# ── Fixtures ──────────────────────────────────────────────────────

TESTS_DIR = Path(__file__).parent
EXAMPLES_DIR = TESTS_DIR.parent / "examples"
GROUND_TRUTH_PATH = TESTS_DIR / "expected" / "ground_truth.json"


@pytest.fixture(scope="module")
def ground_truth():
    """Load the ground truth definitions."""
    with open(GROUND_TRUTH_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_example(filename: str) -> pd.DataFrame:
    """Load an example file as a raw DataFrame (no header)."""
    path = EXAMPLES_DIR / filename
    if filename.endswith(".csv"):
        return pd.read_csv(str(path), header=None, encoding="utf-8-sig")
    elif filename.endswith(".xlsx"):
        return pd.read_excel(str(path), header=None)
    else:
        raise ValueError(f"Unsupported: {filename}")


# ── Parametrize over all example files ────────────────────────────

EXAMPLE_FILES = ["townbusiness1.csv", "townbusiness2.csv", "townbusiness3.csv", "Kor119.xlsx"]


def _skip_if_missing(filename):
    path = EXAMPLES_DIR / filename
    if not path.exists():
        pytest.skip(f"Example file not found: {filename}")


# ═══════════════════════════════════════════════════════════════════
#  Ground Truth — Boundary Range Tests
# ═══════════════════════════════════════════════════════════════════

class TestGroundTruthBoundaries:
    """Validate that detected boundaries fall within expected ranges."""

    @pytest.mark.parametrize("filename", EXAMPLE_FILES)
    def test_top_boundary(self, filename, ground_truth):
        _skip_if_missing(filename)
        gt = ground_truth[filename]
        df = _load_example(filename)
        top, left, bottom, right = find_robust_table_area(df)
        lo, hi = gt["expected_top_range"]
        assert lo <= top <= hi, f"top={top}, expected [{lo}, {hi}]"

    @pytest.mark.parametrize("filename", EXAMPLE_FILES)
    def test_left_boundary(self, filename, ground_truth):
        _skip_if_missing(filename)
        gt = ground_truth[filename]
        df = _load_example(filename)
        top, left, bottom, right = find_robust_table_area(df)
        lo, hi = gt["expected_left_range"]
        assert lo <= left <= hi, f"left={left}, expected [{lo}, {hi}]"

    @pytest.mark.parametrize("filename", EXAMPLE_FILES)
    def test_bottom_boundary(self, filename, ground_truth):
        _skip_if_missing(filename)
        gt = ground_truth[filename]
        df = _load_example(filename)
        top, left, bottom, right = find_robust_table_area(df)
        lo, hi = gt["expected_bottom_range"]
        assert lo <= bottom <= hi, f"bottom={bottom}, expected [{lo}, {hi}]"

    @pytest.mark.parametrize("filename", EXAMPLE_FILES)
    def test_right_boundary(self, filename, ground_truth):
        _skip_if_missing(filename)
        gt = ground_truth[filename]
        df = _load_example(filename)
        top, left, bottom, right = find_robust_table_area(df)
        lo, hi = gt["expected_right_range"]
        assert lo <= right <= hi, f"right={right}, expected [{lo}, {hi}]"


# ═══════════════════════════════════════════════════════════════════
#  Ground Truth — Data Dimension Tests
# ═══════════════════════════════════════════════════════════════════

class TestGroundTruthDimensions:
    """Validate that the extracted area has sufficient rows and columns."""

    @pytest.mark.parametrize("filename", EXAMPLE_FILES)
    def test_min_data_rows(self, filename, ground_truth):
        _skip_if_missing(filename)
        gt = ground_truth[filename]
        df = _load_example(filename)
        top, left, bottom, right = find_robust_table_area(df)
        data_rows = bottom - top
        assert data_rows >= gt["expected_min_data_rows"], \
            f"data_rows={data_rows}, expected >= {gt['expected_min_data_rows']}"

    @pytest.mark.parametrize("filename", EXAMPLE_FILES)
    def test_min_data_cols(self, filename, ground_truth):
        _skip_if_missing(filename)
        gt = ground_truth[filename]
        df = _load_example(filename)
        top, left, bottom, right = find_robust_table_area(df)
        data_cols = right - left
        assert data_cols >= gt["expected_min_data_cols"], \
            f"data_cols={data_cols}, expected >= {gt['expected_min_data_cols']}"


# ═══════════════════════════════════════════════════════════════════
#  Ground Truth — Poison String Tests
# ═══════════════════════════════════════════════════════════════════

class TestGroundTruthPoison:
    """Validate that metadata/comment strings are NOT inside the detected table."""

    @pytest.mark.parametrize("filename", EXAMPLE_FILES)
    def test_no_poison_strings(self, filename, ground_truth):
        _skip_if_missing(filename)
        gt = ground_truth[filename]
        poison = gt.get("poison_strings", [])
        if not poison:
            pytest.skip(f"No poison strings defined for {filename}")

        df = _load_example(filename)
        top, left, bottom, right = find_robust_table_area(df)
        extracted = df.iloc[top:bottom, left:right]

        # Flatten all string values in the extracted area
        all_text = " ".join(
            str(v) for v in extracted.values.flatten()
            if pd.notna(v) and isinstance(v, str)
        )

        for p in poison:
            assert p not in all_text, \
                f"Poison string '{p}' found in extracted table area for {filename}"


# ═══════════════════════════════════════════════════════════════════
#  XLSX Border Detection Tests
# ═══════════════════════════════════════════════════════════════════

class TestBorderDetection:
    """Validate border-based detection on XLSX files."""

    def test_kor119_border_detected(self, ground_truth):
        xlsx_path = str(EXAMPLES_DIR / "Kor119.xlsx")
        _skip_if_missing("Kor119.xlsx")

        result = detect_bordered_area(xlsx_path)
        assert result is not None, "No borders detected in Kor119.xlsx"

        gt_border = ground_truth["Kor119.xlsx"]["border_expected"]
        top, left, bottom, right = result
        assert top == gt_border["top"]
        assert left == gt_border["left"]
        assert bottom == gt_border["bottom"]
        assert right == gt_border["right"]

    def test_kor119_border_vs_standard(self, ground_truth):
        """Border detection should match or improve on standard detection."""
        xlsx_path = str(EXAMPLES_DIR / "Kor119.xlsx")
        _skip_if_missing("Kor119.xlsx")

        df = _load_example("Kor119.xlsx")
        standard = find_robust_table_area(df)
        border = find_robust_table_area_xlsx(df, xlsx_path)

        # Border detection should give at least as good a result
        s_area = (standard[2] - standard[0]) * (standard[3] - standard[1])
        b_area = (border[2] - border[0]) * (border[3] - border[1])
        assert b_area >= s_area * 0.8, \
            f"Border area {b_area} much smaller than standard area {s_area}"

    def test_csv_has_no_borders(self, ground_truth):
        """CSV files should return None from border detection."""
        # We can't call detect_bordered_area on a CSV, but we can verify
        # find_robust_table_area_xlsx falls back gracefully
        _skip_if_missing("townbusiness1.csv")
        df = _load_example("townbusiness1.csv")
        # Pass CSV path as xlsx_path — should fallback to standard
        csv_path = str(EXAMPLES_DIR / "townbusiness1.csv")
        result = find_robust_table_area_xlsx(df, csv_path)
        assert len(result) == 4
        assert result[2] > result[0]  # has valid area

    def test_nonexistent_file_fallback(self):
        """Non-existent XLSX should fallback to standard detection."""
        df = pd.DataFrame([["a", "b"], ["1", "2"], ["3", "4"]])
        result = find_robust_table_area_xlsx(df, "/nonexistent.xlsx")
        assert len(result) == 4


# ═══════════════════════════════════════════════════════════════════
#  Roundtrip — parse() Integration Tests
# ═══════════════════════════════════════════════════════════════════

class TestParseExamplesIntegration:
    """Verify that parse() successfully handles all example files end-to-end."""

    @pytest.mark.parametrize("filename", EXAMPLE_FILES)
    def test_parse_returns_nonempty(self, filename, ground_truth):
        from pynorma import parse
        _skip_if_missing(filename)
        path = str(EXAMPLES_DIR / filename)
        df = parse(path)
        gt = ground_truth[filename]
        assert not df.empty
        assert len(df) >= gt["expected_min_data_rows"] * 0.8
