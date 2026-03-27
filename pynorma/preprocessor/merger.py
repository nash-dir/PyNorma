"""Merger — deduplicate rows by summing numeric columns."""

from typing import List, Union

import pandas as pd


def merge(
    df: pd.DataFrame,
    sum_column: Union[str, List[str]],
) -> pd.DataFrame:
    """Merge duplicate rows by summing specified numeric columns.

    Rows are grouped by all columns **except** *sum_column*.
    The *sum_column* values are aggregated with ``sum()``.

    Parameters
    ----------
    df : pd.DataFrame
        The target DataFrame.
    sum_column : str or list of str
        Numeric column(s) to aggregate.

    Returns
    -------
    pd.DataFrame
        The merged DataFrame.

    Raises
    ------
    ValueError
        If any *sum_column* is not numeric.
    """
    if isinstance(sum_column, str):
        sum_column = [sum_column]

    for col in sum_column:
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise ValueError(f"sum_column '{col}' must be numeric.")

    group_by_cols = df.columns.drop(sum_column).tolist()

    if not group_by_cols:
        return pd.DataFrame(df.sum()).T

    return df.groupby(group_by_cols, as_index=False)[sum_column].sum()
