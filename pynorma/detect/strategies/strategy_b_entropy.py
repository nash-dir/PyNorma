"""
Strategy B: Entropy/Statistical
가설: "엔트로피 변화가 경계를 말해준다"
"""
from __future__ import annotations
from collections import Counter

from ..core import (Strategy, TableRegion, cell_type, is_empty,
                    row_fill_rate, shannon_entropy, grid_cols)


def _row_type_entropy(row: list[str]) -> float:
    types = [cell_type(c) for c in row if cell_type(c) != "empty"]
    if not types:
        return 0.0
    return shannon_entropy(dict(Counter(types)))


class StrategyB(Strategy):
    name = "B_Entropy"
    description = "행별 Shannon entropy 급변 탐지 + 열별 fill rate"

    def detect(self, grid: list[list[str]]) -> list[TableRegion]:
        if not grid:
            return []

        n = len(grid)
        ncols = grid_cols(grid)

        entropies = [_row_type_entropy(row) for row in grid]
        fill_rates = [row_fill_rate(row) for row in grid]

        # Header: entropy 급변 + 타입 변화 최대 지점
        header = 0
        max_delta = -1
        for i in range(min(n - 1, 20)):
            if fill_rates[i] < 0.3:
                continue
            delta = abs(entropies[i] - entropies[i + 1]) if i + 1 < n else 0
            sig_i = [cell_type(c) for c in grid[i] if not is_empty(c)]
            sig_next = [cell_type(c) for c in grid[i + 1] if not is_empty(c)] if i + 1 < n else []
            type_change = sum(1 for a, b in zip(sig_i, sig_next) if a != b) if sig_i and sig_next else 0
            combined = delta + type_change * 0.1
            if combined > max_delta:
                max_delta = combined
                header = i

        top = header + 1

        # Bottom: 역방향 fill < 0.3
        bottom = n - 1
        for i in range(n - 1, top - 1, -1):
            if fill_rates[i] < 0.3:
                bottom = i - 1
            else:
                break
        bottom = max(bottom, top)

        # Left/Right: 열별 fill rate → trim 90%+ 빈 열
        data_row_idxs = [i for i in range(top, bottom + 1) if fill_rates[i] > 0]
        left, right = 0, ncols
        if data_row_idxs:
            for c in range(ncols):
                filled = sum(1 for i in data_row_idxs if c < len(grid[i]) and not is_empty(grid[i][c]))
                if filled / len(data_row_idxs) >= 0.1:
                    left = c
                    break
            for c in range(ncols - 1, left - 1, -1):
                filled = sum(1 for i in data_row_idxs if c < len(grid[i]) and not is_empty(grid[i][c]))
                if filled / len(data_row_idxs) >= 0.1:
                    right = c + 1
                    break

        return [TableRegion(header=header, top=top, left=left, bottom=bottom, right=right)]
