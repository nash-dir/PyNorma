"""Clarifier — standardize column values using a dictionary-based mapping."""

import logging
from typing import List, Optional, Tuple

import pandas as pd

logger = logging.getLogger("pynorma")


def load_clarify_dictionary(path: str) -> List[Tuple[str, str, float]]:
    """Load a clarification dictionary from a CSV file.

    The CSV must have columns ``target``, ``addno``, followed by one or
    more *source* columns.  Uses ``pd.melt`` to convert wide format into
    a list of ``(source, target, addno)`` tuples.

    Parameters
    ----------
    path : str
        Path to the dictionary CSV file.

    Returns
    -------
    list of (str, str, float)
        Mapping entries as ``(source_value, target_value, addno_weight)``.
    """
    df = pd.read_csv(path, dtype=str)

    # All columns after 'target' and 'addno' are source columns
    source_cols = df.columns[2:]

    df_long = df.melt(
        id_vars=["target", "addno"],
        value_vars=source_cols,
        value_name="source",
    )

    df_long.dropna(subset=["source"], inplace=True)
    df_long.drop(columns=["variable"], inplace=True)

    df_long["addno"] = pd.to_numeric(df_long["addno"])
    mapping = [
        (str(row["source"]).strip(), str(row["target"]).strip(), float(row["addno"]))
        for _, row in df_long.iterrows()
    ]

    return mapping


def apply_clarify_mapping(
    df: pd.DataFrame,
    column: str,
    mapping: List[Tuple[str, str, float]],
    addno_col: str = "clarify_addno",
) -> pd.DataFrame:
    """Apply a clarification mapping to a column using vectorized ``map()``.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    column : str
        Column to clarify.
    mapping : list of (str, str, float)
        Mapping entries from :func:`load_clarify_dictionary`.
    addno_col : str
        Name of the temporary weight column.

    Returns
    -------
    pd.DataFrame
        A copy of *df* with the clarified column and addno weights.
    """
    df = df.copy()

    source_to_target = {s: t for s, t, a in mapping}
    source_to_addno = {s: a for s, t, a in mapping}

    original_values = df[column].astype(str).str.strip()

    # Map values; keep originals when no match is found
    df[column] = original_values.map(source_to_target).fillna(original_values)
    df[addno_col] = original_values.map(source_to_addno).fillna(1.0)

    return df


def _merge_rows_fast(
    df: pd.DataFrame,
    key_cols: List[str],
    sum_columns: List[str],
) -> pd.DataFrame:
    """Group by *key_cols* and sum *sum_columns* using ``groupby.agg``."""
    if not key_cols:
        return pd.DataFrame(df[sum_columns].sum()).T

    agg_dict = {col: "sum" for col in sum_columns}
    return df.groupby(key_cols, as_index=False).agg(agg_dict)


def clarify(
    df: pd.DataFrame,
    column: str,
    dict_path: str,
    sum_columns: Optional[List[str]] = None,
    addno_col: str = "clarify_addno",
) -> pd.DataFrame:
    """Clarify a column using a dictionary and optionally merge duplicate rows.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    column : str
        The column to clarify.
    dict_path : str
        Path to the clarification dictionary CSV.
    sum_columns : list of str, optional
        Numeric columns to aggregate when merging duplicates.
    addno_col : str
        Name of the temporary weight column.

    Returns
    -------
    pd.DataFrame
        The clarified (and optionally merged) DataFrame.
    """
    mapping = load_clarify_dictionary(dict_path)
    df = apply_clarify_mapping(df, column, mapping, addno_col=addno_col)

    if sum_columns:
        df = df.copy()

        # Apply addno weights to each sum column
        for col in sum_columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
            df[addno_col] = pd.to_numeric(df[addno_col], errors="coerce").fillna(0)
            df[col] = df[col] * df[addno_col]

        # Group and aggregate
        sum_cols_set = set(sum_columns)
        key_cols = [c for c in df.columns if c not in sum_cols_set and c != addno_col]
        df = _merge_rows_fast(df, key_cols, sum_columns)

    # Drop the temporary addno column
    if addno_col in df.columns:
        df.drop(columns=[addno_col], inplace=True)

    return df