import pandas as pd
from typing import Union, List

def merge(df: pd.DataFrame, 
          sum_column: Union[str, List[str]]
          ) -> pd.DataFrame:
    """Merges rows by summing the values in `sum_column` for rows where all other values are identical.

    This is handled efficiently using Pandas `groupby`.

    Parameters
    ----------
    df : pd.DataFrame
        The target DataFrame.
    sum_column : Union[str, List[str]]
        The numeric column(s) to be summed.

    Returns
    -------
    pd.DataFrame
        The merged DataFrame.
    """
    if isinstance(sum_column, str):
        sum_column = [sum_column]

    # Type check
    for col in sum_column:
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise ValueError(f"sum_column '{col}' must be numeric.")

    # Use all columns except for sum_column as grouping keys.
    group_by_cols = df.columns.drop(sum_column).tolist()

    # If there are no columns to group by (i.e., all columns are in sum_column)
    if not group_by_cols:
        return pd.DataFrame(df.sum()).T

    # Aggregate using groupby and sum
    merged_df = df.groupby(group_by_cols, as_index=False)[sum_column].sum()

    return merged_df
