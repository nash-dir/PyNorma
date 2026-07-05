"""
test_structure.py
=================
Regression tests for the structural layer (Step 1-3):

  1. build_table_model — multi-row header blocks, upward extension,
     units-row absorption, headerless detection, stub detection
  2. to_long — long-form conversion semantics
  3. ground_truth.json integrity
  4. End-to-end evaluation floor (the honest metric: cell-level F1 of the
     final long-form output vs hand-labeled ground truth)
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from benchmark.core import (
    TableModel, read_specimen, build_table_model, to_long,
)
from benchmark.preprocess import detect
from benchmark.evaluate import load_ground_truth, evaluate, SPECIMEN_DIR


def model_for(fname: str, table_index: int = 0) -> tuple[list, TableModel]:
    grid, _ = read_specimen(SPECIMEN_DIR / fname)
    regions = detect(grid)
    assert regions, f"no regions detected in {fname}"
    return grid, build_table_model(grid, regions[table_index])


# ─────────────────────────────────────────────
# 1. build_table_model
# ─────────────────────────────────────────────

class TestBuildTableModel:
    def test_multirow_header_block(self):
        # 12: title rows, then a 2-row header (group / item), units row dropped
        _, m = model_for("12_deep_multiheader.csv")
        assert m.header_rows == (4, 5)
        assert m.stub_end == 1
        assert m.top == 8

    def test_upward_extension_year_row(self):
        # 17: year row (2020..2024) sits ABOVE the row containing 대분류/중분류
        _, m = model_for("17_crosstab_rowheaders.csv")
        assert m.header_rows == (0, 1)
        assert m.stub_end == 2

    def test_units_row_absorbed(self):
        # 20: "(KRW/원)" units row glued under the header
        _, m = model_for("20_mixed_lang_units.csv")
        assert m.header_rows == (0, 1)
        assert m.top == 2

    def test_headerless_numeric(self):
        # 11: pure numeric matrix, no header at all
        _, m = model_for("11_no_header_numeric.csv")
        assert m.header_rows is None
        assert m.top == 0  # first row reclaimed as data

    def test_timestamp_stub(self):
        # 16: leading timestamp column is the row index
        _, m = model_for("16_extreme_sparse.csv")
        assert m.stub_end == 1

    def test_numeric_id_stub(self):
        # 03: sequential integer ID column belongs to the stub
        _, m = model_for("03_encoding_chaos.csv")
        assert m.stub_end >= 1

    def test_no_data_row_extension(self):
        # 13: single-row header must NOT swallow the first data row
        _, m = model_for("13_pivot_crosstab.csv")
        assert m.header_rows == (0, 0)
        assert m.top == 1


# ─────────────────────────────────────────────
# 2. to_long
# ─────────────────────────────────────────────

class TestToLong:
    def test_crosstab_melt(self):
        grid, m = model_for("13_pivot_crosstab.csv")
        cols, rows = to_long(grid, m)
        assert cols[-1] == "value"
        assert ["서울", "전자", "25"] in rows

    def test_multilevel_variables(self):
        grid, m = model_for("12_deep_multiheader.csv")
        cols, rows = to_long(grid, m)
        # 2 header levels → level_1 / level_2 columns
        assert "level_1" in cols and "level_2" in cols
        assert ["1월", "매출", "제품A", "143"] in rows

    def test_stub_forward_fill(self):
        # 17: 대분류 is only written on the first row of each group
        grid, m = model_for("17_crosstab_rowheaders.csv")
        _, rows = to_long(grid, m)
        assert ["전자", "냉장고", "2020", "매출(억)", "52"] in rows

    def test_dropna_skips_empty_cells(self):
        grid, m = model_for("16_extreme_sparse.csv")
        _, rows = to_long(grid, m)
        assert all(r[-1] != "" for r in rows)

    def test_summary_rows_skipped(self):
        grid, m = model_for("06_pivot_style_table.csv")
        _, rows = to_long(grid, m)
        joined = " ".join(v for r in rows for v in r).lower()
        assert "subtotal" not in joined
        assert "grand total" not in joined


# ─────────────────────────────────────────────
# 3. Ground truth integrity
# ─────────────────────────────────────────────

class TestGroundTruth:
    def test_loads_and_files_exist(self):
        gt = load_ground_truth()
        assert len(gt) >= 36
        for fname in gt:
            assert (SPECIMEN_DIR / fname).exists(), f"missing specimen {fname}"

    def test_models_are_consistent(self):
        for fname, models in load_ground_truth().items():
            for m in models:
                assert m.top <= m.bottom, fname
                assert m.left <= m.stub_end < m.right, fname
                if m.header_rows is not None:
                    assert m.header_rows[0] <= m.header_rows[1] < m.top, fname


# ─────────────────────────────────────────────
# 4. Evaluation floor — the honest metric
# ─────────────────────────────────────────────

class TestEvaluationFloor:
    """Regression floor for end-to-end long-form correctness.

    Baselines (2026-07-05): micro F1 0.9992, macro F1 0.9703, 33/36 perfect.
    Known-open cases: 10 (side-by-side tables), 04/08 (ragged columns /
    side-annotation column slightly over-included).
    """

    @pytest.fixture(scope="class")
    def results(self):
        return evaluate(verbose=False)

    def test_micro_f1_floor(self, results):
        assert results["_aggregate"]["micro_f1"] >= 0.98

    def test_macro_f1_floor(self, results):
        assert results["_aggregate"]["macro_f1"] >= 0.94

    def test_perfect_file_count(self, results):
        assert results["_aggregate"]["perfect_files"] >= 31

    def test_no_detection_errors(self, results):
        errors = [k for k, v in results.items()
                  if not k.startswith("_") and "error" in v]
        assert errors == []
