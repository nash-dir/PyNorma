import pandas as pd
import numpy as np
from typing import Optional
from pynorma.utils import find_largest_soft_rectangle
from pynorma.detect.header_finder import detect_header_end_row

_TEMP_DELIMITER = "__SEP__"
_NAN_TOKEN = "[NaN]"


def _concat_rowwise_headers(df, header_rows, header_cols, delimiter=_TEMP_DELIMITER, nan_token=_NAN_TOKEN):
    header_block = df.iloc[header_rows:, :header_cols]
    header_block = header_block.fillna(nan_token).astype(str)
    flat_index = header_block.agg(delimiter.join, axis=1).tolist()
    return flat_index


def detect_header_end_col(df: pd.DataFrame, 
                          header_rows: Optional[int] = None
                          ) -> int:
    """
    Automatically detect the number of header columns in a table
    by locating the left boundary of the largest numeric data block.

    Parameters:
        df (pd.DataFrame): The table DataFrame.
        header_rows (Optional[int]): Number of header rows (to exclude from detection).

    Returns:
        int: Index of the first data column (i.e., header end column).
    """

    if header_rows is None:
        raise ValueError("header_rows must be specified to detect header_cols")

    df_data = df.iloc[header_rows:, :]
    top, bottom, left, right = find_largest_soft_rectangle(
        df_data,
        row_offset=0,
        col_offset=0,
        tolerance=0.3,
        min_score=0.7
    )

    # 보정: 좌표계를 전체 DataFrame 기준으로 변경
    left += 0
    right += 0

    table_width = df.shape[1]
    square_width = right - left

    if square_width / table_width >= 0.8:
        return left
    else:
        raise ValueError("No sufficient data square found: table may not be flattenable.")


def flatten(
    df: pd.DataFrame,
    header_rows: Optional[int] = None,
    header_cols: Optional[int] = None,
    horizontal_feature_names: Optional[list] = None,
    vertical_feature_names: Optional[list] = None,
    data_feature: Optional[str] = "value",
    delimiter: Optional[str] = _TEMP_DELIMITER
) -> pd.DataFrame:
    
    # Step 0: if number of header rows and columns are not manually fed, auto-detect number of header rows and columns
    if header_rows is None:
        header_rows = detect_header_end_row(df)

    if header_cols is None:
        header_cols = detect_header_end_col(df, header_rows)

    # Step 1: create rowwise index
    row_index = _concat_rowwise_headers(df, header_rows, header_cols, delimiter)

    # Step 2: concatenate column-wise headers
    colwise_headers = df.iloc[:header_rows, header_cols:]
    colwise_headers = colwise_headers.fillna(_NAN_TOKEN).astype(str)
    flat_columns = colwise_headers.agg(delimiter.join, axis=0).tolist()

    # Step 3: extract data
    df_data = df.iloc[header_rows:, header_cols:].copy()
    df_data.index = row_index
    df_data.columns = flat_columns

    # Step 4: melt into long-form table
    df_long = df_data.reset_index().melt(id_vars=["index"], var_name="column_key", value_name=data_feature)

    # Step 5: split vertical headers
    vert_parts = df_long["index"].str.split(delimiter, expand=True)
    if vertical_feature_names and len(vertical_feature_names) == vert_parts.shape[1]:
        vert_parts.columns = vertical_feature_names
    else:
        vert_parts.columns = [f"vertical_{i+1}" for i in range(vert_parts.shape[1])]

    # Step 6: split horizontal headers
    horiz_parts = df_long["column_key"].str.split(delimiter, expand=True)
    if horizontal_feature_names and len(horizontal_feature_names) == horiz_parts.shape[1]:
        horiz_parts.columns = horizontal_feature_names
    else:
        horiz_parts.columns = [f"horizontal_{i+1}" for i in range(horiz_parts.shape[1])]

    # Step 7: concatenate vert_parts and horiz_parts
    df_final = pd.concat([vert_parts, horiz_parts, df_long[[data_feature]]], axis=1)
    return df_final
