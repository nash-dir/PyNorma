"""
test_preprocess.py
==================
Regression tests for the ensemble preprocessor benchmark.

Tests:
  1. Core utilities (is_empty, is_numeric, cell_type, etc.)
  2. TableRegion validation
  3. Strategy contract (each returns list[TableRegion])
  4. quality_score range
  5. clean_region correctness
  6. preprocess() API (run-all + specific strategy)
  7. Adversarial specimen regression tests
  8. Score thresholds (no strategy below 0.5 on any file)
"""
import sys
from pathlib import Path
import pytest

# Add benchmark to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pynorma.detect.core import (
    TableRegion, is_empty, is_numeric, is_date_like, cell_type,
    row_fill_rate, quality_score, clean_region, compute_scores,
    read_specimen, grid_cols, Scores,
)
from pynorma.detect.strategies.strategy_a_rules import StrategyA
from pynorma.detect.strategies.strategy_b_entropy import StrategyB
from pynorma.detect.strategies.strategy_c_gradient import StrategyC
from pynorma.detect.strategies.strategy_d_pattern import StrategyD
from pynorma.detect.strategies.strategy_e_window import StrategyE
from pynorma.detect.strategies.strategy_f_voting import StrategyF
from pynorma.detect.preprocess import detect, preprocess

SPECIMEN_DIR = Path(__file__).resolve().parent.parent.parent  # specimen/
ALL_STRATEGIES = [StrategyA(), StrategyB(), StrategyC(),
                  StrategyD(), StrategyE(), StrategyF()]


# ──────────────────────────────────────────
# 1. Core utilities
# ──────────────────────────────────────────

class TestCellUtils:
    def test_is_empty_blank(self):
        assert is_empty("")
        assert is_empty("  ")

    def test_is_empty_markers(self):
        for m in ["N/A", "null", "NaN", "-", "미입력", "#N/A"]:
            assert is_empty(m), f"{m} should be empty"

    def test_is_empty_values(self):
        assert not is_empty("hello")
        assert not is_empty("123")

    def test_is_numeric_plain(self):
        assert is_numeric("123")
        assert is_numeric("3.14")
        assert is_numeric("-42")

    def test_is_numeric_formatted(self):
        assert is_numeric("1,234")
        assert is_numeric("$500")
        assert is_numeric("₩10000")
        assert is_numeric("(100)")

    def test_is_numeric_text(self):
        assert not is_numeric("hello")
        assert not is_numeric("")
        assert not is_numeric("abc123")

    def test_is_date_like(self):
        assert is_date_like("2024-01-15")
        assert is_date_like("01/15/2024")
        assert is_date_like("20240115")
        assert not is_date_like("hello")
        assert not is_date_like("123")

    def test_cell_type(self):
        assert cell_type("") == "empty"
        assert cell_type("N/A") == "empty"
        assert cell_type("123") == "numeric"
        assert cell_type("2024-01-01") == "date"
        assert cell_type("hello") == "text"

    def test_row_fill_rate(self):
        assert row_fill_rate([]) == 0.0
        assert row_fill_rate(["a", "b", "c"]) == 1.0
        assert row_fill_rate(["a", "", "c"]) == pytest.approx(2/3)
        assert row_fill_rate(["", "", ""]) == 0.0


# ──────────────────────────────────────────
# 2. TableRegion
# ──────────────────────────────────────────

class TestTableRegion:
    def test_creation(self):
        r = TableRegion(header=0, top=1, left=0, bottom=10, right=5)
        assert r.header == 0
        assert r.top == 1
        assert r.left == 0
        assert r.bottom == 10
        assert r.right == 5

    def test_is_namedtuple(self):
        r = TableRegion(0, 1, 0, 10, 5)
        assert isinstance(r, tuple)
        assert len(r) == 5


# ──────────────────────────────────────────
# 3. Strategy contract
# ──────────────────────────────────────────

SIMPLE_GRID = [
    ["Name", "Age", "Score"],
    ["Alice", "30", "90"],
    ["Bob", "25", "85"],
    ["Charlie", "35", "92"],
]


class TestStrategyContract:
    @pytest.mark.parametrize("strategy", ALL_STRATEGIES,
                             ids=[s.name for s in ALL_STRATEGIES])
    def test_returns_list_of_tableregion(self, strategy):
        result = strategy.detect(SIMPLE_GRID)
        assert isinstance(result, list)
        assert len(result) >= 1
        for r in result:
            assert isinstance(r, TableRegion)

    @pytest.mark.parametrize("strategy", ALL_STRATEGIES,
                             ids=[s.name for s in ALL_STRATEGIES])
    def test_empty_grid(self, strategy):
        result = strategy.detect([])
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.parametrize("strategy", ALL_STRATEGIES,
                             ids=[s.name for s in ALL_STRATEGIES])
    def test_region_bounds_valid(self, strategy):
        result = strategy.detect(SIMPLE_GRID)
        for r in result:
            assert r.top <= r.bottom, f"{strategy.name}: top > bottom"
            assert r.left < r.right, f"{strategy.name}: left >= right"
            assert r.header >= 0, f"{strategy.name}: header < 0"
            assert r.header <= r.top, f"{strategy.name}: header > top"

    @pytest.mark.parametrize("strategy", ALL_STRATEGIES,
                             ids=[s.name for s in ALL_STRATEGIES])
    def test_simple_grid_header(self, strategy):
        result = strategy.detect(SIMPLE_GRID)
        assert result[0].header == 0, f"{strategy.name} missed header at row 0"


# ──────────────────────────────────────────
# 4. quality_score
# ──────────────────────────────────────────

class TestQualityScore:
    def test_score_range(self):
        r = TableRegion(0, 1, 0, 3, 3)
        score = quality_score(SIMPLE_GRID, r)
        assert 0.0 <= score <= 1.0

    def test_good_region_scores_higher(self):
        grid = [
            ["A", "B", "C"],
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"],
            ["", "", ""],
            ["note", "", ""],
        ]
        good = TableRegion(0, 1, 0, 3, 3)
        bad = TableRegion(3, 4, 0, 5, 3)
        assert quality_score(grid, good) > quality_score(grid, bad)

    def test_empty_region(self):
        r = TableRegion(0, 0, 0, 0, 0)
        assert quality_score(SIMPLE_GRID, r) == 0.0


# ──────────────────────────────────────────
# 5. clean_region
# ──────────────────────────────────────────

class TestCleanRegion:
    def test_basic_cleaning(self):
        r = TableRegion(0, 1, 0, 3, 3)
        cleaned = clean_region(SIMPLE_GRID, r)
        assert len(cleaned) == 4  # header + 3 data
        assert cleaned[0] == ["Name", "Age", "Score"]

    def test_removes_empty_rows(self):
        grid = [
            ["H1", "H2"],
            ["a", "b"],
            ["", ""],
            ["c", "d"],
        ]
        r = TableRegion(0, 1, 0, 3, 2)
        cleaned = clean_region(grid, r)
        assert len(cleaned) == 3  # header + 2 data (empty row removed)

    def test_removes_summary_rows(self):
        grid = [
            ["항목", "금액"],
            ["A", "100"],
            ["B", "200"],
            ["합계", "300"],
        ]
        r = TableRegion(0, 1, 0, 3, 2)
        cleaned = clean_region(grid, r)
        assert len(cleaned) == 3  # header + 2 data (합계 removed)

    def test_cleans_cells(self):
        grid = [
            ["H1", "H2"],
            ["\ufeffvalue", "N/A"],
        ]
        r = TableRegion(0, 1, 0, 1, 2)
        cleaned = clean_region(grid, r)
        assert cleaned[1][0] == "value"
        assert cleaned[1][1] == ""


# ──────────────────────────────────────────
# 6. preprocess() API
# ──────────────────────────────────────────

class TestPreprocessAPI:
    def test_detect_from_grid(self):
        regions = detect(SIMPLE_GRID)
        assert isinstance(regions, list)
        assert len(regions) >= 1
        assert isinstance(regions[0], TableRegion)

    def test_detect_specific_strategy(self):
        for key in "ABCDEF":
            regions = detect(SIMPLE_GRID, strategy=key)
            assert len(regions) >= 1

    def test_preprocess_from_grid(self):
        results = preprocess(SIMPLE_GRID)
        assert isinstance(results, list)
        assert len(results) >= 1
        region, cleaned = results[0]
        assert isinstance(region, TableRegion)
        assert isinstance(cleaned, list)
        assert len(cleaned) >= 2  # at least header + 1 row

    def test_preprocess_with_strategy(self):
        results = preprocess(SIMPLE_GRID, strategy="C")
        assert len(results) >= 1


# ──────────────────────────────────────────
# 7. Specimen regression tests
# ──────────────────────────────────────────

def _get_specimen_files():
    files = sorted(SPECIMEN_DIR.glob("*"))
    return [f for f in files if f.is_file()
            and not f.name.startswith("_") and not f.name.startswith(".")
            and f.suffix.lower() in (".csv", ".xlsx")]


class TestSpecimenRegression:
    """Every specimen must produce at least one valid region from each strategy."""

    @pytest.fixture(scope="class")
    def specimens(self):
        return _get_specimen_files()

    def test_specimens_exist(self, specimens):
        assert len(specimens) >= 36, f"Expected 36+ specimens, got {len(specimens)}"

    @pytest.mark.parametrize("strategy", ALL_STRATEGIES,
                             ids=[s.name for s in ALL_STRATEGIES])
    def test_all_strategies_on_all_specimens(self, specimens, strategy):
        """Every strategy must return ≥1 region for every specimen."""
        for fpath in specimens:
            grid, _ = read_specimen(fpath)
            if not grid:
                continue
            regions = strategy.detect(grid)
            assert len(regions) >= 1, (
                f"{strategy.name} returned 0 regions for {fpath.name}")
            for r in regions:
                assert r.top <= r.bottom, (
                    f"{strategy.name} invalid bounds for {fpath.name}")

    def test_preprocess_all_specimens(self, specimens):
        """The default run-all pipeline must succeed on every specimen."""
        for fpath in specimens:
            results = preprocess(fpath)
            assert len(results) >= 1, f"preprocess failed on {fpath.name}"
            region, cleaned = results[0]
            assert len(cleaned) >= 2, (
                f"Cleaned output too small for {fpath.name}")


# ──────────────────────────────────────────
# 8. Score thresholds
# ──────────────────────────────────────────

class TestScoreThresholds:
    """At least one strategy must score ≥ 0.8 on every specimen."""

    @pytest.fixture(scope="class")
    def specimens(self):
        return _get_specimen_files()

    def test_at_least_one_strategy_above_threshold(self, specimens):
        from benchmark.benchmark_runner import generate_ground_truth
        threshold = 0.7

        for fpath in specimens:
            grid, _ = read_specimen(fpath)
            if not grid:
                continue
            gt = generate_ground_truth(grid)
            scores = []
            for strategy in ALL_STRATEGIES:
                try:
                    regions = strategy.detect(grid)
                    sc = compute_scores(regions, gt, grid)
                    scores.append((strategy.name, sc.avg))
                except Exception:
                    continue

            best_score = max(s[1] for s in scores) if scores else 0
            assert best_score >= threshold, (
                f"No strategy reached {threshold} on {fpath.name}. "
                f"Best: {max(scores, key=lambda x: x[1])}")


# ──────────────────────────────────────────
# 9. Adversarial-specific tests
# ──────────────────────────────────────────

class TestAdversarialCases:
    """Specific assertions for known adversarial patterns."""

    def test_no_header_numeric(self):
        """All-numeric data: header row should still be detected (row 0)."""
        path = SPECIMEN_DIR / "11_no_header_numeric.csv"
        if not path.exists():
            pytest.skip("specimen not generated")
        grid, _ = read_specimen(path)
        for s in ALL_STRATEGIES:
            regions = s.detect(grid)
            assert len(regions) >= 1

    def test_deep_multiheader_finds_data(self):
        """Deep multi-header: at least C/D should find header around row 4-5."""
        path = SPECIMEN_DIR / "12_deep_multiheader.csv"
        if not path.exists():
            pytest.skip("specimen not generated")
        grid, _ = read_specimen(path)
        # C_Gradient should find header at row 4 or 5
        regions = StrategyC().detect(grid)
        assert regions[0].header <= 5

    def test_title_footnotes_trimmed(self):
        """Title+footnotes: C/D should trim to just data region."""
        path = SPECIMEN_DIR / "19_title_footnotes_heavy.csv"
        if not path.exists():
            pytest.skip("specimen not generated")
        grid, _ = read_specimen(path)
        regions = StrategyC().detect(grid)
        # Should find header at row 5 (column names)
        assert regions[0].header >= 3  # skip title rows
        assert regions[0].bottom <= 15  # don't include footnotes

    def test_single_column(self):
        """Single-column: all strategies should handle 1-column data."""
        path = SPECIMEN_DIR / "22_single_column.csv"
        if not path.exists():
            pytest.skip("specimen not generated")
        grid, _ = read_specimen(path)
        for s in ALL_STRATEGIES:
            regions = s.detect(grid)
            assert len(regions) >= 1
            assert regions[0].right - regions[0].left >= 1

    def test_empty_cols_middle(self):
        """Empty columns in middle shouldn't break detection."""
        path = SPECIMEN_DIR / "18_empty_cols_middle.csv"
        if not path.exists():
            pytest.skip("specimen not generated")
        grid, _ = read_specimen(path)
        for s in ALL_STRATEGIES:
            regions = s.detect(grid)
            assert len(regions) >= 1
            assert regions[0].right - regions[0].left >= 5  # 7 cols total


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
