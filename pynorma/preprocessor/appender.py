"""Append (vertically concatenate) two DataFrames with smart header handling."""

import logging
from typing import Any, Dict, Literal, Optional, Union

import pandas as pd

logger = logging.getLogger("pynorma")


def isthere_header(df: pd.DataFrame) -> bool:
    """Check whether a DataFrame appears to have a meaningful header.

    Returns ``True`` if the column index is **not** a plain ``RangeIndex``
    and does **not** consist entirely of ``Unnamed:`` labels.
    """
    if df.empty:
        return False
    cols = df.shape[1]
    is_integer_index = list(df.columns) == list(range(cols))
    is_unnamed_index = all(
        isinstance(c, str) and c.startswith("Unnamed:") for c in df.columns
    )
    return not (is_integer_index or is_unnamed_index)


def append(
    df1: Any,
    df2: Any,
    strict: bool = False,
    recover_types: bool = False,
    verbose: bool = False,
    df2_header: Union[bool, Literal["auto"]] = "auto",
) -> Optional[pd.DataFrame]:
    """Vertically concatenate two DataFrames (or parser result tuples).

    Parameters
    ----------
    df1 : pd.DataFrame or tuple
        Base DataFrame (or a ``(DataFrame, info)`` tuple from a parser).
    df2 : pd.DataFrame or tuple
        DataFrame to append.
    strict : bool
        If ``True``, raise on any structural mismatch.
    recover_types : bool
        If ``True``, attempt to cast *df2* columns to *df1* dtypes.
    verbose : bool
        If ``True``, log diagnostic messages.
    df2_header : bool or ``"auto"``
        Whether *df2* has its own header.  ``"auto"`` uses heuristic
        detection.

    Returns
    -------
    pd.DataFrame or None
        The concatenated result.
    """
    # Unwrap parser tuples
    if isinstance(df1, tuple) and len(df1) > 0 and isinstance(df1[0], pd.DataFrame):
        df1 = df1[0]
    if isinstance(df2, tuple) and len(df2) > 0 and isinstance(df2[0], pd.DataFrame):
        df2 = df2[0]

    if df2_header == "auto":
        df2_has_header = isthere_header(df2)
    else:
        df2_has_header = df2_header

    if df2_has_header:
        structure = compare_structure(df1, df2)
        if verbose:
            logger.info("[Append] Structure diff: %s", structure)
        if strict and (
            structure["missing_in_df2"]
            or structure["extra_in_df2"]
            or structure["dtype_mismatch"]
        ):
            raise ValueError("DataFrame structure mismatch: strict mode enabled.")

        df2_reindexed = df2.reindex(columns=df1.columns, fill_value=pd.NA)

        if recover_types:
            common_cols = df1.columns.intersection(df2.columns)
            for col in common_cols:
                dtype1 = df1[col].dtype
                try:
                    df2_reindexed[col] = df2_reindexed[col].astype(dtype1)
                except (ValueError, TypeError):
                    if verbose:
                        logger.info("[Append] Failed to cast df2['%s'] to %s", col, dtype1)

        result = pd.concat([df1, df2_reindexed], ignore_index=True)

    else:
        # df2 has no header — align by column count
        num_cols_df1 = df1.shape[1]
        num_cols_df2 = df2.shape[1]

        if num_cols_df1 != num_cols_df2:
            if verbose:
                logger.warning(
                    "[Append] Column count mismatch in no-header mode. "
                    "Adjusting df2 from %d to %d columns.",
                    num_cols_df2,
                    num_cols_df1,
                )

            if num_cols_df2 > num_cols_df1:
                df2 = df2.iloc[:, :num_cols_df1]
            else:
                for i in range(num_cols_df1 - num_cols_df2):
                    df2[f"__pynorma_added_col_{i}"] = pd.NA

        df2.columns = df1.columns
        result = pd.concat([df1, df2], ignore_index=True)
        if verbose:
            logger.info("[Append] Concatenated by shape (no header in df2).")

    return result


def compare_structure(df1: pd.DataFrame, df2: pd.DataFrame) -> Dict[str, object]:
    """Compare the column structure of two DataFrames.

    Returns
    -------
    dict
        Keys: ``missing_in_df2``, ``extra_in_df2``, ``dtype_mismatch``.
    """
    cols1 = set(df1.columns)
    cols2 = set(df2.columns)

    missing_in_df2 = list(cols1 - cols2)
    extra_in_df2 = list(cols2 - cols1)

    dtype_mismatch = {}
    for col in cols1.intersection(cols2):
        if df1[col].dtype != df2[col].dtype:
            dtype_mismatch[col] = (str(df1[col].dtype), str(df2[col].dtype))

    return {
        "missing_in_df2": missing_in_df2,
        "extra_in_df2": extra_in_df2,
        "dtype_mismatch": dtype_mismatch,
    }
