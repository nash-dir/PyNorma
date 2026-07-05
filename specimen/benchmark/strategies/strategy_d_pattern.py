"""
Strategy D: Pattern-First Normalizer
가설: "정규식으로 먼저 정규화하면 구조가 드러난다"
"""
from __future__ import annotations
import re
from ..core import (Strategy, TableRegion, is_empty, is_numeric,
                    row_fill_rate, grid_cols, clean_cell)


def _normalize(val: str) -> str:
    v = clean_cell(val)
    if not v:
        return ""
    # date: MM/DD/YYYY → YYYY-MM-DD
    m = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})$", v)
    if m:
        return f"{m.group(3)}-{m.group(1).zfill(2)}-{m.group(2).zfill(2)}"
    # currency: $1,234 → 1234
    m = re.match(r"^[\$₩€£]\s*([\d,]+\.?\d*)$", v)
    if m:
        return m.group(1).replace(",", "")
    # European decimal: 1.234,56 → 1234.56
    m = re.match(r"^(\d{1,3}(?:\.\d{3})*),(\d+)$", v)
    if m:
        return f"{m.group(1).replace('.', '')}.{m.group(2)}"
    return v


class StrategyD(Strategy):
    name = "D_Pattern"
    description = "정규식 선행 정규화 후 타입 비율 기반 데이터 영역 판별"

    def detect(self, grid: list[list[str]]) -> list[TableRegion]:
        if not grid:
            return []

        n = len(grid)
        ncols = grid_cols(grid)

        # Normalize all cells first
        norm = [[_normalize(grid[r][c]) if c < len(grid[r]) else ""
                 for c in range(ncols)] for r in range(n)]

        # Header: first row with >50% text among non-empty
        header = 0
        for i in range(min(n, 20)):
            non_empty = [c for c in norm[i] if c]
            if len(non_empty) < 2:
                continue
            text_count = sum(1 for c in non_empty if not is_numeric(c))
            if text_count / len(non_empty) > 0.5:
                header = i
                break

        top = header + 1

        # Bottom: last row with fill >= 0.3
        bottom = n - 1
        for i in range(n - 1, top - 1, -1):
            if row_fill_rate(norm[i]) >= 0.3:
                bottom = i
                break

        # Column boundaries
        data_idxs = [i for i in range(top, bottom + 1) if row_fill_rate(norm[i]) > 0]
        left, right = 0, ncols
        if data_idxs:
            for c in range(ncols):
                filled = sum(1 for i in data_idxs if norm[i][c])
                if filled / len(data_idxs) >= 0.1:
                    left = c
                    break
            for c in range(ncols - 1, left - 1, -1):
                filled = sum(1 for i in data_idxs if norm[i][c])
                if filled / len(data_idxs) >= 0.1:
                    right = c + 1
                    break

        return [TableRegion(header=header, top=top, left=left,
                            bottom=bottom, right=right)]
