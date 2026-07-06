"""Flattener — convert wide, multi-level header tables into a tidy long format."""

import logging
from typing import List, Optional

import pandas as pd

from pynorma.utils import find_largest_soft_rectangle
from pynorma.detect.header_finder import detect_header_end_row

logger = logging.getLogger("pynorma")

_TEMP_DELIMITER = "__SEP__"
_NAN_TOKEN = "[NaN]"


def _concat_rowwise_headers(
    df: pd.DataFrame,
    header_rows: int,
    header_cols: int,
    delimiter: str = _TEMP_DELIMITER,
    nan_token: str = _NAN_TOKEN,
) -> List[str]:
    """Concatenate row-wise header cells into flat index strings."""
    header_block = df.iloc[header_rows:, :header_cols]
    header_block = header_block.fillna(nan_token).astype(str)
    flat_index = header_block.agg(delimiter.join, axis=1).tolist()
    return flat_index


def detect_header_end_col(
    df: pd.DataFrame,
    header_rows: Optional[int] = None,
) -> int:
    """Detect the number of header columns (row-index columns).

    Locates the left boundary of the largest numeric data block.

    Parameters
    ----------
    df : pd.DataFrame
        The table DataFrame.
    header_rows : int
        Number of header rows (to exclude from detection).

    Returns
    -------
    int
        Index of the first data column.

    Raises
    ------
    ValueError
        If *header_rows* is ``None`` or no sufficient data block is found.
    """
    if header_rows is None:
        raise ValueError("header_rows must be specified to detect header_cols")

    df_data = df.iloc[header_rows:, :]
    top, bottom, left, right = find_largest_soft_rectangle(
        df_data,
        row_offset=0,
        col_offset=0,
        tolerance=0.3,
        min_score=0.7,
    )

    table_width = df.shape[1]
    square_width = right - left

    if square_width / table_width >= 0.8:
        return left
    else:
        raise ValueError("No sufficient data block found: table may not be flattenable.")


def flatten(
    df: pd.DataFrame,
    header_rows: Optional[int] = None,
    header_cols: Optional[int] = None,
    horizontal_feature_names: Optional[List[str]] = None,
    vertical_feature_names: Optional[List[str]] = None,
    data_feature: Optional[str] = "value",
    delimiter: Optional[str] = _TEMP_DELIMITER,
) -> pd.DataFrame:
    """Convert a wide, multi-level header table into a tidy long-format DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Input table with multi-level row and/or column headers.
    header_rows : int, optional
        Number of header rows.  ``None`` triggers auto-detection.
    header_cols : int, optional
        Number of header columns.  ``None`` triggers auto-detection.
    horizontal_feature_names : list of str, optional
        Custom names for the column-header levels.
    vertical_feature_names : list of str, optional
        Custom names for the row-header levels.
    data_feature : str
        Name for the value column in the melted output.
    delimiter : str
        Internal delimiter used to join header levels.

    Returns
    -------
    pd.DataFrame
        A tidy long-format DataFrame.
    """
    # Step 0: auto-detect header dimensions if not provided
    if header_rows is None:
        header_rows = detect_header_end_row(df)

    if header_cols is None:
        header_cols = detect_header_end_col(df, header_rows)

    # Step 1: build row-wise index
    row_index = _concat_rowwise_headers(df, header_rows, header_cols, delimiter)

    # Step 2: build column-wise flat headers
    colwise_headers = df.iloc[:header_rows, header_cols:]
    colwise_headers = colwise_headers.fillna(_NAN_TOKEN).astype(str)
    flat_columns = colwise_headers.agg(delimiter.join, axis=0).tolist()

    # Step 3: extract data block
    df_data = df.iloc[header_rows:, header_cols:].copy()
    df_data.index = row_index
    df_data.columns = flat_columns

    # Step 4: melt into long form
    df_long = df_data.reset_index().melt(
        id_vars=["index"], var_name="column_key", value_name=data_feature
    )

    # Step 5: split vertical (row) headers
    vert_parts = df_long["index"].str.split(delimiter, expand=True)
    if vertical_feature_names and len(vertical_feature_names) == vert_parts.shape[1]:
        vert_parts.columns = vertical_feature_names
    else:
        vert_parts.columns = [f"vertical_{i + 1}" for i in range(vert_parts.shape[1])]

    # Step 6: split horizontal (column) headers
    horiz_parts = df_long["column_key"].str.split(delimiter, expand=True)
    if horizontal_feature_names and len(horizontal_feature_names) == horiz_parts.shape[1]:
        horiz_parts.columns = horizontal_feature_names
    else:
        horiz_parts.columns = [f"horizontal_{i + 1}" for i in range(horiz_parts.shape[1])]

    # Step 7: combine all parts
    df_final = pd.concat([vert_parts, horiz_parts, df_long[[data_feature]]], axis=1)
    return df_final
