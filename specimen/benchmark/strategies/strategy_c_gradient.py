"""
Strategy C: Gradient Boundary Detection
가설: "밀도 기울기(gradient)가 테이블을 정의한다"
"""
from __future__ import annotations

from ..core import (Strategy, TableRegion, is_empty, is_numeric,
                    row_fill_rate, row_fill_count, grid_cols)


class StrategyC(Strategy):
    name = "C_Gradient"
    description = "행/열 fill count 1차 미분으로 density cliff 탐지"

    def detect(self, grid: list[list[str]]) -> list[TableRegion]:
        if not grid:
            return []

        n = len(grid)
        ncols = grid_cols(grid)

        # Row fill counts + normalize
        row_fills = [row_fill_count(row) for row in grid]
        max_fill = max(row_fills) if row_fills else 1
        if max_fill == 0:
            return []
        normalized = [f / max_fill for f in row_fills]

        # Top: first row with density >= 0.3
        top_bound = 0
        for i in range(n):
            if normalized[i] >= 0.3:
                top_bound = i
                break

        # Bottom: last row with density >= 0.3
        bottom_bound = n - 1
        for i in range(n - 1, top_bound, -1):
            if normalized[i] >= 0.3:
                bottom_bound = i
                break

        # Header: first text-dominant row in top region
        header = top_bound
        for i in range(top_bound, min(top_bound + 10, bottom_bound)):
            non_empty = [c for c in grid[i] if not is_empty(c)]
            if len(non_empty) < 2:
                continue
            text_ratio = sum(1 for c in non_empty if not is_numeric(c)) / len(non_empty)
            if text_ratio > 0.5:
                header = i
                break

        top = header + 1

        # Column projection within data rows
        col_fills = [0] * ncols
        count = 0
        for i in range(top, bottom_bound + 1):
            if row_fill_rate(grid[i]) == 0:
                continue
            count += 1
            for j in range(min(ncols, len(grid[i]))):
                if not is_empty(grid[i][j]):
                    col_fills[j] += 1

        left, right = 0, ncols
        if count > 0:
            for j in range(ncols):
                if col_fills[j] / count >= 0.1:
                    left = j
                    break
            for j in range(ncols - 1, left - 1, -1):
                if col_fills[j] / count >= 0.1:
                    right = j + 1
                    break

        return [TableRegion(header=header, top=top, left=left,
                            bottom=bottom_bound, right=right)]
