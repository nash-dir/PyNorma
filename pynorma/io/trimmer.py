"""
Smart DataFrame trimmer.

Combines table-area detection with header assignment to produce a
cleanly cropped DataFrame from a raw, messy input.

Supports two detection backends:
  - **ensemble** (default): 6 competing strategies via quality_score
  - **legacy**: gradient-based table_finder (fallback)
"""

import logging
from typing import Dict, Literal, Optional, Tuple, Union

import pandas as pd

from pynorma.detect.table_finder import find_robust_table_area
from pynorma.detect.header_finder import detect_header_end_row

logger = logging.getLogger("pynorma")


def _try_ensemble_detect(df: pd.DataFrame) -> Optional[Tuple[int, int, int, int, int]]:
    """Try ensemble detection, returning (header, top, left, bottom, right) or None."""
    try:
        from pynorma.detect.preprocess import detect as ensemble_detect

        # Convert DataFrame to grid
        grid = []
        for idx in range(len(df)):
            row = [str(v) if pd.notna(v) else "" for v in df.iloc[idx]]
            grid.append(row)

        if not grid:
            return None

        regions = ensemble_detect(grid)
        if not regions:
            return None

        r = regions[0]
        return (r.header, r.top, r.left, r.bottom, r.right)
    except Exception:
        return None


def trim_dataframe(
    df: pd.DataFrame,
    trim_mode: Union[bool, Literal["auto"], dict] = "auto",
    set_header: bool = True,
    header_row: Optional[int] = None,
) -> Tuple[pd.DataFrame, Dict]:
    """Trim unnecessary rows/columns and optionally set the header row.

    Parameters
    ----------
    df : pd.DataFrame
        The raw DataFrame to trim.
    trim_mode : bool or ``"auto"`` or dict
        - ``"auto"``: auto-detect the table region (ensemble → legacy fallback).
        - ``False``: skip trimming.
        - ``dict``: manual coordinates ``{'top', 'bottom', 'left', 'right'}``.
    set_header : bool
        Whether to promote a detected/specified row to column headers.
    header_row : int or None
        Absolute row index of the header.  ``None`` triggers auto-detection
        within the trimmed area.

    Returns
    -------
    tuple of (pd.DataFrame, dict)
        The trimmed DataFrame and a metadata dict containing shape info,
        trim boundaries, and the resolved header position.
    """
    df_trimmed = df.copy()
    original_shape = df.shape

    top, left, bottom, right = 0, 0, original_shape[0], original_shape[1]
    top_offset = 0
    ensemble_header = None

    # 1. Trim based on *trim_mode*
    if trim_mode == "auto":
        # Try ensemble detection first
        result = _try_ensemble_detect(df)
        if result is not None:
            ensemble_header, top, left, bottom, right = result
            bottom = min(bottom + 1, original_shape[0])  # TableRegion.bottom is inclusive
            right = min(right, original_shape[1])
            logger.debug("Trimmer: ensemble detection → header=%d, data=[%d..%d], cols=[%d..%d)",
                         ensemble_header, top, bottom, left, right)
        else:
            # Fallback to legacy gradient-based detection
            top, left, bottom, right = find_robust_table_area(df)
            logger.debug("Trimmer: legacy detection → [%d..%d, %d..%d)", top, bottom, left, right)

        df_trimmed = df.iloc[top:bottom, left:right].reset_index(drop=True)
        top_offset = top
    elif isinstance(trim_mode, dict):
        top = trim_mode.get("top", 0)
        bottom = trim_mode.get("bottom", original_shape[0])
        left = trim_mode.get("left", 0)
        right = trim_mode.get("right", original_shape[1])
        df_trimmed = df.iloc[top:bottom, left:right].reset_index(drop=True)
        top_offset = top
    elif trim_mode is False:
        pass
    else:
        raise ValueError("'trim_mode' must be 'auto', False, or a dict.")

    # 2. Assign header row
    final_header_row_abs = header_row

    if set_header and not df_trimmed.empty:
        header_to_set = header_row

        if header_to_set is None:
            if ensemble_header is not None:
                # The ensemble region's top is the first DATA row, so the
                # header row is not inside df_trimmed — take it from the
                # original frame directly.
                if 0 <= ensemble_header < original_shape[0]:
                    df_trimmed.columns = list(df.iloc[ensemble_header, left:right])
                    final_header_row_abs = ensemble_header
            else:
                # Auto-detect via legacy header_finder
                last_comment_row = detect_header_end_row(df_trimmed)
                if last_comment_row != -1:
                    header_to_set = last_comment_row + 1  # relative
                    final_header_row_abs = top_offset + header_to_set

        if header_to_set is not None:
            # Convert to relative index if the value came from the caller
            if header_row is not None:
                header_row_relative = header_to_set - top_offset
            else:
                header_row_relative = header_to_set

            if 0 <= header_row_relative < len(df_trimmed):
                df_trimmed.columns = df_trimmed.iloc[header_row_relative]
                df_trimmed = df_trimmed.iloc[header_row_relative + 1:].reset_index(drop=True)

    # 3. Build metadata for verbose output
    trim_info = {
        "original_shape": original_shape,
        "trimmed_shape": df_trimmed.shape,
        "top": top,
        "bottom": bottom,
        "left": left,
        "right": right,
        "header_row_abs": final_header_row_abs,
        "detection_method": "ensemble" if ensemble_header is not None else "legacy",
    }

    return df_trimmed, trim_info

