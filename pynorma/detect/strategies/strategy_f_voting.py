"""
Strategy F: Type-Consistency Voter
가설: "열 타입 일관성으로 투표하면 노이즈를 걸러낸다"
"""
from __future__ import annotations
from collections import Counter

from ..core import (Strategy, TableRegion, cell_type, is_empty, is_numeric,
                    row_fill_rate, grid_cols)


class StrategyF(Strategy):
    name = "F_Voting"
    description = "열별 주 타입 결정 후 행마다 타입 일치도 투표"

    VOTE_THRESHOLD = 0.5

    def detect(self, grid: list[list[str]]) -> list[TableRegion]:
        if not grid:
            return []

        n = len(grid)
        ncols = grid_cols(grid)

        # Preliminary header
        header = 0
        for i in range(min(n, 20)):
            non_empty = [c for c in grid[i] if not is_empty(c)]
            if len(non_empty) < 2:
                continue
            text_ratio = sum(1 for c in non_empty if not is_numeric(c)) / len(non_empty)
            if text_ratio > 0.5:
                header = i
                break

        # Column dominant types (from all rows after header)
        col_type_counts: list[Counter] = [Counter() for _ in range(ncols)]
        for row in grid[header + 1:]:
            for j in range(min(ncols, len(row))):
                t = cell_type(row[j])
                if t != "empty":
                    col_type_counts[j][t] += 1

        col_dominant = []
        for j in range(ncols):
            if col_type_counts[j]:
                col_dominant.append(col_type_counts[j].most_common(1)[0][0])
            else:
                col_dominant.append(None)

        # Vote each row
        data_rows = []
        for i in range(header + 1, n):
            if row_fill_rate(grid[i]) == 0:
                continue
            votes, total = 0, 0
            for j in range(min(ncols, len(grid[i]))):
                if col_dominant[j] is None:
                    continue
                total += 1
                t = cell_type(grid[i][j])
                if t == "empty":
                    votes += 0.5
                elif t == col_dominant[j]:
                    votes += 1.0
                elif t in ("numeric", "date") and col_dominant[j] in ("numeric", "date"):
                    votes += 0.8
            score = votes / max(total, 1)
            if score >= self.VOTE_THRESHOLD:
                data_rows.append(i)

        if not data_rows:
            return [TableRegion(header=header, top=header + 1, left=0,
                                bottom=n - 1, right=ncols)]

        top = min(data_rows)
        bottom = max(data_rows)

        # Column boundaries: exclude cols with no dominant type
        left, right = 0, ncols
        for j in range(ncols):
            if col_dominant[j] is not None:
                left = j
                break
        for j in range(ncols - 1, left - 1, -1):
            if col_dominant[j] is not None:
                right = j + 1
                break

        return [TableRegion(header=header, top=top, left=left,
                            bottom=bottom, right=right)]
