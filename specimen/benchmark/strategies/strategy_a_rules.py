"""
Strategy A: Rule-Based Heuristic
가설: "고정 규칙이면 충분하다"
"""
from __future__ import annotations
from ..core import (Strategy, TableRegion, is_empty, is_numeric,
                    row_fill_rate, grid_cols, has_summary_keyword)


class StrategyA(Strategy):
    name = "A_Rules"
    description = "고정 규칙: 첫 비빈행=헤더, 역방향 푸터 스캔"

    def detect(self, grid: list[list[str]]) -> list[TableRegion]:
        if not grid:
            return []

        n = len(grid)
        ncols = grid_cols(grid)

        # Header: 첫 번째 fill > 0.5 행
        header = 0
        for i in range(min(n, 20)):
            if row_fill_rate(grid[i]) > 0.5:
                header = i
                break

        # Bottom: 역방향 스캔, fill >= 0.3이고 소계 아닌 마지막 행
        bottom = n - 1
        for i in range(n - 1, header, -1):
            row = grid[i]
            fr = row_fill_rate(row)
            if fr == 0 or (fr < 0.3) or has_summary_keyword(row):
                bottom = i - 1
            else:
                break
        bottom = max(bottom, header + 1)

        top = header + 1
        left = 0
        right = ncols

        return [TableRegion(header=header, top=top, left=left, bottom=bottom, right=right)]
