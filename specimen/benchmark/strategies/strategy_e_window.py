"""
Strategy E: Density-Window Scanner
가설: "슬라이딩 윈도우로 가장 밀도 높은 블록을 찾는다"
"""
from __future__ import annotations
from ..core import (Strategy, TableRegion, is_empty, is_numeric,
                    row_fill_rate, grid_cols)


class StrategyE(Strategy):
    name = "E_Window"
    description = "슬라이딩 윈도우 이동평균 fill rate 기반 최대 밀도 구간"

    WINDOW_SIZE = 5
    DENSITY_THRESHOLD = 0.4

    def detect(self, grid: list[list[str]]) -> list[TableRegion]:
        if not grid:
            return []

        n = len(grid)
        ncols = grid_cols(grid)
        w = min(self.WINDOW_SIZE, max(1, n // 4))

        fill_rates = [row_fill_rate(row) for row in grid]

        # Moving average
        moving_avg = [0.0] * n
        for i in range(n):
            start = max(0, i - w // 2)
            end = min(n, i + w // 2 + 1)
            moving_avg[i] = sum(fill_rates[start:end]) / (end - start)

        # Longest high-density contiguous segment
        best_start, best_end, best_score = 0, 0, 0
        cur_start = None
        cur_score = 0

        for i in range(n):
            if moving_avg[i] >= self.DENSITY_THRESHOLD:
                if cur_start is None:
                    cur_start = i
                cur_score += moving_avg[i]
            else:
                if cur_start is not None:
                    if cur_score > best_score:
                        best_start, best_end, best_score = cur_start, i - 1, cur_score
                    cur_start = None
                    cur_score = 0
        if cur_start is not None and cur_score > best_score:
            best_start, best_end = cur_start, n - 1

        # Fallback: if no segment found, use full grid
        if best_end <= best_start:
            best_start, best_end = 0, n - 1

        # Header within segment
        header = best_start
        for i in range(best_start, min(best_start + 10, best_end)):
            non_empty = [c for c in grid[i] if not is_empty(c)]
            if len(non_empty) < 2:
                continue
            text_ratio = sum(1 for c in non_empty if not is_numeric(c)) / len(non_empty)
            if text_ratio > 0.5:
                header = i
                break

        top = header + 1
        bottom = max(best_end, top)  # ensure top <= bottom

        # Column boundaries
        data_idxs = [i for i in range(top, bottom + 1) if fill_rates[i] > 0]
        left, right = 0, ncols
        if data_idxs:
            for c in range(ncols):
                filled = sum(1 for i in data_idxs if c < len(grid[i]) and not is_empty(grid[i][c]))
                if filled / len(data_idxs) >= 0.1:
                    left = c
                    break
            for c in range(ncols - 1, left - 1, -1):
                filled = sum(1 for i in data_idxs if c < len(grid[i]) and not is_empty(grid[i][c]))
                if filled / len(data_idxs) >= 0.1:
                    right = c + 1
                    break

        return [TableRegion(header=header, top=top, left=left,
                            bottom=bottom, right=right)]
