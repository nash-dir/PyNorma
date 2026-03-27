"""
XLSX cell-border detection for table boundary extraction.

When an XLSX file has styled cell borders, they provide a **near-perfect**
signal for locating the exact table area — far more reliable than any
content-based heuristic.  This module reads the openpyxl workbook and
returns the bounding box of the bordered region.
"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger("pynorma")


def detect_bordered_area(
    xlsx_path: str,
    sheet_name: Optional[str] = None,
) -> Optional[Tuple[int, int, int, int]]:
    """Detect the bounding box of the bordered cell region in an XLSX file.

    Scans every cell for non-None border styles (thin, medium, thick, etc.)
    and returns the smallest rectangle that contains all bordered cells.

    Parameters
    ----------
    xlsx_path : str
        Path to the ``.xlsx`` file.
    sheet_name : str, optional
        Sheet name to inspect.  If ``None``, uses the active sheet.

    Returns
    -------
    tuple of int or None
        ``(top, left, bottom, right)`` in 0-indexed DataFrame coordinates,
        or ``None`` if no bordered cells are found.

    Notes
    -----
    - Coordinates are returned as **0-indexed** (matching pandas iloc),
      not openpyxl's 1-indexed convention.
    - The result is a half-open interval: ``[top, bottom)`` rows,
      ``[left, right)`` columns.
    """
    try:
        import openpyxl
    except ImportError:
        logger.debug("openpyxl not installed — border detection unavailable.")
        return None

    try:
        wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=False)
    except Exception:
        logger.debug("Failed to load workbook for border detection: %s", xlsx_path)
        return None

    ws = wb[sheet_name] if sheet_name else wb.active

    min_row, min_col = None, None
    max_row, max_col = None, None

    for row in ws.iter_rows():
        for cell in row:
            b = cell.border
            has_border = (
                (b.top and b.top.style)
                or (b.bottom and b.bottom.style)
                or (b.left and b.left.style)
                or (b.right and b.right.style)
            )
            if has_border:
                r = cell.row - 1  # 0-indexed
                c = cell.column - 1  # 0-indexed
                if min_row is None or r < min_row:
                    min_row = r
                if max_row is None or r > max_row:
                    max_row = r
                if min_col is None or c < min_col:
                    min_col = c
                if max_col is None or c > max_col:
                    max_col = c

    wb.close()

    if min_row is None:
        return None

    # Convert to half-open [top, bottom)
    return (min_row, min_col, max_row + 1, max_col + 1)
