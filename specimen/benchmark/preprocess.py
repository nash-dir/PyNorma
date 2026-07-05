"""
preprocess.py — Public entry point for PyNorma table detection + cleaning.

Usage:
    from specimen.benchmark.preprocess import preprocess

    results = preprocess("data.csv")                   # run-all (default)
    results = preprocess("data.csv", strategy="C")     # specific strategy
    results = preprocess("data.csv", strategy="auto")  # explicit run-all

Each result = (TableRegion, cleaned_rows)
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .core import (
    TableRegion, Strategy, quality_score, clean_region,
    read_specimen, grid_cols, split_tables_by_gap, segment_blocks,
)
from .strategies.strategy_a_rules import StrategyA
from .strategies.strategy_b_entropy import StrategyB
from .strategies.strategy_c_gradient import StrategyC
from .strategies.strategy_d_pattern import StrategyD
from .strategies.strategy_e_window import StrategyE
from .strategies.strategy_f_voting import StrategyF


ALL_STRATEGIES: dict[str, Strategy] = {
    "A": StrategyA(),
    "B": StrategyB(),
    "C": StrategyC(),
    "D": StrategyD(),
    "E": StrategyE(),
    "F": StrategyF(),
}


def _select_best(
    grid: list[list[str]],
    candidates: dict[str, list[TableRegion]],
) -> list[TableRegion]:
    """Run-all: pick the strategy whose regions score highest."""
    best_score = -1.0
    best_regions: list[TableRegion] = []
    best_name = ""

    for name, regions in candidates.items():
        if not regions:
            continue
        # Score = average quality_score across all detected regions
        scores = [quality_score(grid, r) for r in regions]
        avg = sum(scores) / len(scores)
        if avg > best_score:
            best_score = avg
            best_regions = regions
            best_name = name

    return best_regions


def _detect_single_table(
    grid: list[list[str]],
    strategy: Optional[str] = None,
) -> list[TableRegion]:
    """Detect a single table region using strategies."""
    if strategy and strategy.upper() in ALL_STRATEGIES:
        return ALL_STRATEGIES[strategy.upper()].detect(grid)

    # Run all → auto-select
    candidates = {}
    for name, strat in ALL_STRATEGIES.items():
        try:
            candidates[name] = strat.detect(grid)
        except Exception:
            continue

    return _select_best(grid, candidates)


def _detect_in_block(grid, block, strategy) -> Optional[TableRegion]:
    """Detect one table inside a segmentation block (absolute coordinates).

    The block is sliced out, run through single-table detection, and the
    resulting region is offset back into whole-grid coordinates.
    """
    r0, r1, c0, c1 = block
    sub = [[grid[r][c] if (r < len(grid) and c < len(grid[r])) else ""
            for c in range(c0, c1 + 1)]
           for r in range(r0, r1 + 1)]
    regions = _detect_single_table(sub, strategy)
    if not regions:
        return None
    reg = regions[0]
    return TableRegion(
        header=(reg.header + r0) if reg.header >= 0 else -1,
        top=reg.top + r0, left=reg.left + c0,
        bottom=reg.bottom + r0, right=reg.right + c0,
    )


def _block_is_valid(grid, reg: TableRegion) -> bool:
    """A block detection is a real table if it has ≥2 data rows, ≥1 column,
    and scores above a floor — filters out sliver/noise blocks."""
    if reg.bottom - reg.top + 1 < 2 or reg.right - reg.left < 1:
        return False
    return quality_score(grid, reg) >= 0.45


def detect(
    path_or_grid: Path | str | list[list[str]],
    *,
    strategy: Optional[str] = None,
) -> list[TableRegion]:
    """Detect table regions (supports multi-table sheets).

    Parameters
    ----------
    path_or_grid : Path, str, or 2D list
        File path or pre-loaded grid.
    strategy : str, optional
        "A"~"F" for specific strategy, or None/"auto" for run-all.

    Returns
    -------
    list[TableRegion]
        Detected table regions (may be > 1 for multi-table sheets).
    """
    if isinstance(path_or_grid, (str, Path)):
        grid, _ = read_specimen(Path(path_or_grid))
    else:
        grid = path_or_grid

    if not grid:
        return []

    # Recursive layout segmentation: cut the sheet into content blocks along
    # empty column bands (side-by-side tables) and blank-row / section-title
    # boundaries (stacked tables), then detect one table per block. Only trust
    # a multi-block split when it yields ≥2 valid tables; otherwise fall back
    # to whole-grid single-table detection.
    blocks = segment_blocks(grid)
    if len(blocks) >= 2:
        regions = []
        for blk in blocks:
            reg = _detect_in_block(grid, blk, strategy)
            if reg is not None and _block_is_valid(grid, reg):
                regions.append(reg)
        if len(regions) >= 2:
            return regions

    # Single table: use strategy competition over the whole grid.
    return _detect_single_table(grid, strategy)


def preprocess(
    path_or_grid: Path | str | list[list[str]],
    *,
    strategy: Optional[str] = None,
) -> list[tuple[TableRegion, list[list[str]]]]:
    """Full pipeline: detect + clean.

    Parameters
    ----------
    path_or_grid : Path, str, or 2D list
        File path or pre-loaded grid.
    strategy : str, optional
        "A"~"F" for specific, None/"auto" for run-all.

    Returns
    -------
    list of (TableRegion, cleaned_rows)
        One entry per detected table.
    """
    if isinstance(path_or_grid, (str, Path)):
        grid, _ = read_specimen(Path(path_or_grid))
    else:
        grid = path_or_grid

    regions = detect(grid, strategy=strategy)
    return [(r, clean_region(grid, r)) for r in regions]
