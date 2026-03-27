"""
Detect the boundary row between header/comment rows and data rows.

Uses type-signature analysis: each row is converted to a tuple of
``('string', 'numeric', 'empty')`` labels, and the pair of consecutive
rows with the largest signature change is identified as the header
boundary.
"""

import pandas as pd
from typing import Tuple

from pynorma.utils import classify_cell


def _get_row_type_signature(row: pd.Series) -> Tuple[str, ...]:
    """Return a per-cell type signature for a single DataFrame row.

    Each cell is classified as ``'empty'``, ``'numeric'``, or ``'string'``
    using the shared :func:`pynorma.utils.classify_cell` classifier.
    """
    return tuple(classify_cell(v) for v in row)


def detect_header_end_row(
    df: pd.DataFrame,
    max_search_rows: int = 20,
    *,
    numeric_row_threshold: float = 0.8,
    string_row_threshold: float = 0.6,
    min_diff_count: int = 2,
) -> int:
    """Detect the last header (or comment) row by analysing type-signature changes.

    Scans the first *max_search_rows* rows and finds the pair of
    consecutive rows with the largest type-signature difference.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to analyse.
    max_search_rows : int
        Maximum number of rows to scan from the top.
    numeric_row_threshold : float
        If a row is more than this fraction numeric it is likely data,
        not a comment row, and is skipped as a candidate boundary.
    string_row_threshold : float
        If the first row exceeds this fraction of string cells it is
        assumed to be a single-row header.
    min_diff_count : int
        Minimum number of type changes required to consider a boundary
        meaningful.

    Returns
    -------
    int
        Index of the last comment/header row, or ``-1`` if none found.
    """
    if len(df) < 2:
        return -1

    search_range = min(len(df) - 1, max_search_rows)
    signatures = [_get_row_type_signature(df.iloc[i]) for i in range(search_range + 1)]

    max_diff = -1
    header_end_index = -1

    # Compare consecutive row type signatures
    for i in range(1, search_range):
        sig1 = signatures[i]
        sig2 = signatures[i + 1]

        diff_count = sum(1 for t1, t2 in zip(sig1, sig2) if t1 != t2)

        # Skip rows that are mostly numeric (likely data, not header)
        is_mostly_numeric = sig1.count("numeric") / len(sig1) > numeric_row_threshold

        if diff_count > max_diff and not is_mostly_numeric:
            max_diff = diff_count
            header_end_index = i

    # Confidence check: require at least *min_diff_count* type changes
    if max_diff >= min_diff_count:
        return header_end_index
    else:
        # If there is barely any change, check whether the first row
        # looks like a text header.
        if signatures and signatures[0].count("string") / len(signatures[0]) > string_row_threshold:
            return 0  # single-row header
        return -1
