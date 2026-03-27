"""
Locate the main data-table region within a messy DataFrame.

**V2 Architecture — 3-Phase Pipeline**:

1. **Gradient-Based Projection** — estimate a generous bounding box by
   analysing the first derivative (gradient) of row/column fill rates
   to detect density "cliffs".
2. **Header Detection** — within the bounding box, locate the exact
   header row so that leading comment rows are removed.
3. **Type Consistency Refinement** — shrink border columns/rows whose
   type entropy is too high (= likely annotations, not data).
"""

import logging
from typing import Tuple

import numpy as np
import pandas as pd

from pynorma.detect.header_finder import detect_header_end_row
from pynorma.utils import classify_cell

logger = logging.getLogger("pynorma")


# ═══════════════════════════════════════════════════════════════════
#  Phase 1: Gradient-Based Projection
# ═══════════════════════════════════════════════════════════════════

def _find_boundary_by_gradient(
    projection: np.ndarray,
    *,
    cliff_threshold: float = 0.3,
    min_density: float = 0.3,
) -> Tuple[int, int]:
    """Find the start/end of the dense region in a 1-D projection.

    Uses gradient (first derivative) analysis to locate density "cliffs"
    where the fill rate drops sharply.

    Parameters
    ----------
    projection : np.ndarray
        Per-row or per-column count of non-empty cells.
    cliff_threshold : float
        Minimum normalised drop to count as a cliff.
    min_density : float
        Minimum normalised density for a row/column to be considered
        part of the table.

    Returns
    -------
    tuple of int
        ``(start, end)`` — half-open interval ``[start, end)``.
    """
    n = len(projection)
    if n == 0:
        return 0, 0

    max_val = projection.max()
    if max_val == 0:
        return 0, 0

    normalized = projection / max_val

    # Forward scan: find first index that reaches min_density
    start = 0
    for i in range(n):
        if normalized[i] >= min_density:
            start = i
            break

    # Backward scan: find last index that still holds min_density
    end = n
    for i in range(n - 1, -1, -1):
        if normalized[i] >= min_density:
            end = i + 1
            break

    return int(start), int(end)


def _find_table_by_projection(df: pd.DataFrame) -> Tuple[int, int, int, int]:
    """Estimate the table boundary using gradient-aware row/column projections.

    Returns
    -------
    tuple of int
        ``(top, left, bottom, right)``
    """
    if df.empty:
        return 0, 0, 0, 0

    df_cleaned = df.replace(r"^\s*$", pd.NA, regex=True)
    binary_matrix = df_cleaned.notna().astype(int)

    # Row projection
    row_projection = binary_matrix.sum(axis=1).values

    if row_projection.max() == 0:
        return 0, 0, 0, 0

    top, bottom = _find_boundary_by_gradient(row_projection)

    if top >= bottom:
        return 0, 0, 0, 0

    # Column projection (within the detected row range only)
    col_projection = binary_matrix.iloc[top:bottom].sum(axis=0).values
    left, right = _find_boundary_by_gradient(col_projection)

    if left >= right:
        return 0, 0, 0, 0

    return top, left, bottom, right


# ═══════════════════════════════════════════════════════════════════
#  Phase 3: Type Consistency Refinement
# ═══════════════════════════════════════════════════════════════════

def _column_type_entropy(series: pd.Series) -> float:
    """Compute Shannon entropy over the type distribution of a column.

    Returns
    -------
    float
        ``0.0`` = perfectly uniform type (pure data).
        ``~1.58`` = string, numeric, empty all equally present (noisy).
    """
    types = series.apply(classify_cell)
    counts = types.value_counts(normalize=True)
    return float(-sum(p * np.log2(p) for p in counts if p > 0))


def _column_fill_rate(series: pd.Series) -> float:
    """Return the fraction of non-empty cells in a Series."""
    types = series.apply(classify_cell)
    return float((types != "empty").mean())


def _should_trim_series(
    series: pd.Series,
    *,
    entropy_threshold: float,
    min_fill_rate: float,
) -> bool:
    """Decide whether a border column/row looks like annotation noise.

    A column is considered noisy if:
    - Its fill rate is below ``min_fill_rate``, **or**
    - Its type entropy exceeds ``entropy_threshold``.
    """
    fill = _column_fill_rate(series)
    if fill < min_fill_rate:
        return True
    entropy = _column_type_entropy(series)
    if entropy > entropy_threshold:
        return True
    return False


def _refine_boundaries_by_type(
    df: pd.DataFrame,
    top: int,
    left: int,
    bottom: int,
    right: int,
    *,
    entropy_threshold: float = 1.0,
    min_fill_rate: float = 0.3,
    max_shrink: int = 3,
    min_area_ratio: float = 0.2,
) -> Tuple[int, int, int, int]:
    """Shrink the bounding box by removing noisy border columns/rows.

    Scans from each edge inward and stops as soon as a "clean" column
    (or row) is encountered.

    Safety nets
    -----------
    - At most ``max_shrink`` columns/rows are removed per side.
    - If the result area drops below ``min_area_ratio`` of the original
      bounding box, the shrink is rolled back entirely.

    Parameters
    ----------
    df : pd.DataFrame
        The full raw DataFrame.
    top, left, bottom, right : int
        Current bounding box (from Phase 1 + 2).
    entropy_threshold : float
        Columns/rows with entropy above this are trimmed.
    min_fill_rate : float
        Columns/rows with fill rate below this are trimmed.
    max_shrink : int
        Max columns/rows to remove per edge.
    min_area_ratio : float
        Safety: if remaining area < ratio * original, revert.

    Returns
    -------
    tuple of int
        Refined ``(top, left, bottom, right)``.
    """
    original_area = (bottom - top) * (right - left)
    if original_area == 0:
        return top, left, bottom, right

    # Skip refinement for very small tables
    width = right - left
    height = bottom - top
    if width <= 3 or height <= 3:
        return top, left, bottom, right

    new_left, new_right = left, right
    new_top, new_bottom = top, bottom

    # --- Phase 3a: Shrink ROWS first (bottom/top) using full column span ---
    # Row-level footnotes/notes span the entire width, so evaluate with
    # the original left..right *before* any column shrinkage.

    # --- Shrink from bottom ---
    for _ in range(min(max_shrink, height - 3)):
        row_idx = new_bottom - 1
        row_series = df.iloc[row_idx, new_left:new_right]
        if _should_trim_series(row_series, entropy_threshold=entropy_threshold, min_fill_rate=min_fill_rate):
            new_bottom -= 1
        else:
            break

    # --- Shrink from top ---
    for _ in range(min(max_shrink, new_bottom - new_top - 3)):
        row_series = df.iloc[new_top, new_left:new_right]
        if _should_trim_series(row_series, entropy_threshold=entropy_threshold, min_fill_rate=min_fill_rate):
            new_top += 1
        else:
            break

    # --- Phase 3b: Shrink COLUMNS (right/left) using refined row range ---

    # --- Shrink from right ---
    for _ in range(min(max_shrink, width - 3)):
        col_idx = new_right - 1
        col_series = df.iloc[new_top:new_bottom, col_idx]
        if _should_trim_series(col_series, entropy_threshold=entropy_threshold, min_fill_rate=min_fill_rate):
            new_right -= 1
        else:
            break

    # --- Shrink from left ---
    for _ in range(min(max_shrink, new_right - new_left - 3)):
        col_series = df.iloc[new_top:new_bottom, new_left]
        if _should_trim_series(col_series, entropy_threshold=entropy_threshold, min_fill_rate=min_fill_rate):
            new_left += 1
        else:
            break

    # Safety: check area ratio
    new_area = (new_bottom - new_top) * (new_right - new_left)
    if new_area < original_area * min_area_ratio:
        logger.debug(
            "Type-refinement shrank area from %d to %d (%.1f%%), reverting.",
            original_area, new_area, 100 * new_area / original_area,
        )
        return top, left, bottom, right

    return new_top, new_left, new_bottom, new_right


# ═══════════════════════════════════════════════════════════════════
#  Public API
# ═══════════════════════════════════════════════════════════════════

def find_robust_table_area(
    df: pd.DataFrame,
    *,
    entropy_threshold: float = 1.0,
    min_fill_rate: float = 0.3,
    max_shrink: int = 3,
) -> Tuple[int, int, int, int]:
    """Find the main table area using a 3-Phase hybrid pipeline.

    1. **Gradient Projection** — generous bounding box via density
       gradient analysis.
    2. **Header Detection** — precise start row via type-signature
       change detection.
    3. **Type Consistency** — shrink noisy border columns/rows whose
       type entropy or fill rate indicates annotation rather than data.

    Parameters
    ----------
    df : pd.DataFrame
        The raw DataFrame to analyse.
    entropy_threshold : float
        Phase 3: columns/rows with Shannon entropy above this are trimmed.
    min_fill_rate : float
        Phase 3: columns/rows with fill rate below this are trimmed.
    max_shrink : int
        Phase 3: max columns/rows to remove per edge.

    Returns
    -------
    tuple of int
        ``(top, left, bottom, right)``
    """
    # Phase 1: Gradient-Based Projection
    top, left, bottom, right = _find_table_by_projection(df)

    if bottom == 0 and right == 0:
        return 0, 0, 0, 0

    # Phase 2: Header Detection
    df_candidate = df.iloc[top:bottom, left:right]
    header_end_row_relative = detect_header_end_row(df_candidate)

    if header_end_row_relative != -1:
        top = top + header_end_row_relative

        # Re-calculate left/right from the header row itself
        header_series = df.iloc[top].replace(r"^\s*$", pd.NA, regex=True)
        valid_header_indices = header_series.notna().to_numpy().nonzero()[0]

        if len(valid_header_indices) > 0:
            left = int(valid_header_indices[0])
            right = int(valid_header_indices[-1] + 1)

    # Phase 3: Type Consistency Refinement
    top, left, bottom, right = _refine_boundaries_by_type(
        df, top, left, bottom, right,
        entropy_threshold=entropy_threshold,
        min_fill_rate=min_fill_rate,
        max_shrink=max_shrink,
    )

    return top, left, bottom, right


def find_robust_table_area_xlsx(
    df: pd.DataFrame,
    xlsx_path: str,
    sheet_name: str = None,
    *,
    entropy_threshold: float = 1.0,
    min_fill_rate: float = 0.3,
    max_shrink: int = 3,
) -> Tuple[int, int, int, int]:
    """Find the table area in an XLSX file using border detection as a priority signal.

    **Phase 0: Border Detection** — if the XLSX file has styled cell borders,
    they provide a near-perfect table boundary.  If borders are found covering
    a meaningful area (≥10% of the sheet), the bordered rectangle is used
    directly and further heuristics are skipped.

    If no borders are found, falls back to the standard 3-Phase pipeline
    (gradient projection + header detection + type consistency).

    Parameters
    ----------
    df : pd.DataFrame
        The already-loaded raw DataFrame.
    xlsx_path : str
        Path to the ``.xlsx`` file (for openpyxl border scanning).
    sheet_name : str, optional
        Sheet name to inspect for borders.
    entropy_threshold, min_fill_rate, max_shrink
        Passed to the fallback :func:`find_robust_table_area`.

    Returns
    -------
    tuple of int
        ``(top, left, bottom, right)``
    """
    from pynorma.detect.border_detector import detect_bordered_area

    border_area = detect_bordered_area(xlsx_path, sheet_name=sheet_name)

    if border_area is not None:
        b_top, b_left, b_bottom, b_right = border_area
        total_cells = df.shape[0] * df.shape[1]
        bordered_cells = (b_bottom - b_top) * (b_right - b_left)

        # Only trust borders if they cover a meaningful portion of the sheet
        if total_cells > 0 and bordered_cells / total_cells >= 0.10:
            logger.debug(
                "Border detection found table at (%d,%d,%d,%d), area=%d (%.1f%% of sheet)",
                b_top, b_left, b_bottom, b_right,
                bordered_cells, 100 * bordered_cells / total_cells,
            )
            return border_area

    # Fallback to standard 3-Phase pipeline
    return find_robust_table_area(
        df,
        entropy_threshold=entropy_threshold,
        min_fill_rate=min_fill_rate,
        max_shrink=max_shrink,
    )
