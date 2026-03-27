"""
Shared utility functions used across the PyNorma library.

Includes encoding detection, NaN-like value replacement, DataFrame
cleaning, and the largest-soft-rectangle algorithm.
"""

import logging
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
import chardet

from . import config

logger = logging.getLogger("pynorma")


# ---------------------------------------------------------------------------
# Input / Output helpers
# ---------------------------------------------------------------------------

def detect_encoding(file_path: str) -> str:
    """Detect the character encoding of a file using *chardet*.

    Parameters
    ----------
    file_path : str
        Path to the file.

    Returns
    -------
    str
        The detected encoding string (e.g. ``"utf-8"``, ``"cp949"``).
    """
    with open(file_path, "rb") as f:
        raw_data = f.read()
    result = chardet.detect(raw_data)
    return result["encoding"]


# ---------------------------------------------------------------------------
# DataFrame cleaning
# ---------------------------------------------------------------------------

def replace_nan_like(
    df: pd.DataFrame,
    custom_na_values: Optional[List[str]] = None,
) -> pd.DataFrame:
    """Replace NaN-like placeholder values with ``pd.NA``.

    The built-in list is loaded from ``config/nan_like.txt``.
    Additional values can be supplied via *custom_na_values*.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to clean.
    custom_na_values : list of str, optional
        Extra values to treat as missing.

    Returns
    -------
    pd.DataFrame
        A copy of *df* with NaN-like values replaced.
    """
    df_cleaned = df.copy()

    na_values_from_dict = config.get_nan_like()
    na_values_from_list = custom_na_values if custom_na_values else []
    all_na_values = list(set(na_values_from_dict + na_values_from_list))

    if all_na_values:
        df_cleaned.replace(all_na_values, pd.NA, inplace=True)

    return df_cleaned


def clean_dataframe(
    df: pd.DataFrame,
    custom_na_values: Optional[List[str]] = None,
) -> pd.DataFrame:
    """Clean a DataFrame by converting blank strings and NaN-like values to ``pd.NA``.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to clean.
    custom_na_values : list of str, optional
        Extra values to treat as missing.

    Returns
    -------
    pd.DataFrame
        The cleaned DataFrame.
    """
    cleaned = df.map(lambda x: pd.NA if isinstance(x, str) and x.strip() == "" else x)
    cleaned = replace_nan_like(cleaned, custom_na_values)
    return cleaned


# ---------------------------------------------------------------------------
# Cell-level type classification
# ---------------------------------------------------------------------------

def classify_cell(value) -> str:
    """Classify a single cell value as ``'empty'``, ``'numeric'``, or ``'string'``.

    This is the canonical type classifier used by both header detection
    and table-boundary refinement.

    Parameters
    ----------
    value
        Any cell value (string, number, None, pd.NA, np.nan, etc.)

    Returns
    -------
    str
        One of ``'empty'``, ``'numeric'``, ``'string'``.
    """
    if pd.isna(value) or str(value).strip() == "":
        return "empty"
    s = str(value)
    if s.isdigit():
        return "numeric"
    try:
        float(s)
        return "numeric"
    except (ValueError, TypeError):
        return "string"


# ---------------------------------------------------------------------------
# Largest Soft Rectangle
# ---------------------------------------------------------------------------

def find_largest_soft_rectangle(
    df,
    row_offset: int = 0,
    col_offset: int = 0,
    tolerance: float = 0.1,
    min_score: float = 0.8,
) -> Tuple[int, int, int, int]:
    """Find the largest rectangle of numeric-like data within a DataFrame.

    Uses a histogram-based approach (Largest Rectangle in Histogram) with
    fuzzy tolerance for sparse cells.  Non-numeric cells that match known
    NaN-like values are treated as valid.

    Parameters
    ----------
    df : pd.DataFrame or np.ndarray
        Input DataFrame or pre-computed binary mask.
    row_offset : int
        Number of rows to skip from the top.
    col_offset : int
        Number of columns to skip from the left.
    tolerance : float
        Maximum allowed proportion of ``0`` cells in a candidate region.
    min_score : float
        Minimum numeric density to qualify as a valid rectangle.

    Returns
    -------
    tuple of int
        ``(top, bottom, left, right)`` indices of the best rectangle.
    """
    na_like_set = set(config.get_nan_like())

    def is_numeric_or_nanlike(x):
        if pd.isna(x):
            return True
        if isinstance(x, str) and x.strip() in na_like_set:
            return True
        try:
            float(x)
            return True
        except (ValueError, TypeError):
            return False

    # Build binary mask
    if isinstance(df, pd.DataFrame):
        binary_mask = df.map(is_numeric_or_nanlike).astype(int).values
    elif isinstance(df, np.ndarray):
        binary_mask = df  # assume already binary
    else:
        raise TypeError("Input must be a pandas DataFrame or numpy ndarray")

    rows, cols = binary_mask.shape
    max_area = 0
    best_rect = (0, 0, 0, 0)
    heights = [0] * cols

    # Iterate row-by-row, maintaining a histogram of column heights
    for i in range(row_offset, rows):
        for j in range(col_offset, cols):
            if binary_mask[i][j]:
                heights[j] += 1
            else:
                heights[j] = 0

        # Standard Largest-Rectangle-in-Histogram via a monotonic stack
        stack: list[int] = []
        for j in range(cols + 1):
            curr_height = heights[j] if j < cols else 0
            while stack and curr_height < heights[stack[-1]]:
                h = heights[stack.pop()]
                w = j if not stack else j - stack[-1] - 1
                left = stack[-1] + 1 if stack else 0
                top = i - h + 1
                bottom = i + 1
                right = j

                region = binary_mask[top:bottom, left:right]
                total = h * w
                zeros = (region == 0).sum()
                score = (total - zeros) / total if total > 0 else 0

                if zeros <= total * tolerance and score >= min_score:
                    if total > max_area:
                        max_area = total
                        best_rect = (top, bottom, left, right)

            stack.append(j)

    return best_rect
