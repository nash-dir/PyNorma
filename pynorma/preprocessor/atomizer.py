"""Atomizer — split multi-valued cells into separate rows or columns."""

import logging
from typing import List, Optional, Union

import pandas as pd

from .. import config

logger = logging.getLogger("pynorma")


def detect_feature_delimiter(
    series: pd.Series,
    candidates: Optional[List[str]] = None,
    *,
    min_score: float = 0.1,
) -> Optional[str]:
    """Detect the most likely in-cell delimiter for a Series.

    Each *candidate* delimiter is scored by the proportion of non-null
    cells that would be split into two or more parts.

    Parameters
    ----------
    series : pd.Series
        The column to analyse.
    candidates : list of str, optional
        Candidate delimiters.  Defaults to the built-in list from
        ``config/delimiters.txt``.
    min_score : float
        Minimum proportion of cells that must be splittable for a
        delimiter to be accepted.

    Returns
    -------
    str or None
        The detected delimiter, or ``None`` if no delimiter passes the
        threshold.
    """
    if candidates is None:
        candidates = config.get_delimiters()

    total = len(series)
    best_delim = None
    max_score = 0

    for delim in candidates:
        count = (
            series.dropna()
            .astype(str)
            .apply(lambda x, d=delim: len(x.split(d)) > 1)
            .sum()
        )
        score = count / total
        if score > max_score:
            max_score = score
            best_delim = delim

    return best_delim if max_score > min_score else None


def atomize_by_column(
    df: pd.DataFrame,
    atm_cols: Optional[Union[str, List[str]]] = None,
    delimiter: Optional[str] = None,
) -> pd.DataFrame:
    """Explode multi-valued cells into separate rows (column-wise atomization).

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to atomize.
    atm_cols : str or list of str, optional
        Columns to atomize.  ``None`` triggers auto-detection.
    delimiter : str, optional
        The delimiter to split on.  ``None`` triggers per-column
        auto-detection.

    Returns
    -------
    pd.DataFrame
        The atomized DataFrame.
    """
    df = df.copy()

    if isinstance(atm_cols, str):
        atm_cols = [atm_cols]

    # Auto-detect target columns
    if atm_cols is None:
        atm_cols = []
        for col in df.columns:
            delim = detect_feature_delimiter(df[col])
            if delim:
                atm_cols.append(col)

    for col in atm_cols:
        this_delim = delimiter or detect_feature_delimiter(df[col])
        if not this_delim:
            continue
        df[col] = df[col].astype(str).str.split(this_delim)
        df[col] = df[col].apply(lambda x: [i.strip() for i in x if i.strip() != ""])
        df = df.explode(col).reset_index(drop=True)

    return df


def atomize_by_row(
    df: pd.DataFrame,
    atm_cols: Optional[Union[str, List[str]]] = None,
    delimiter: Optional[str] = None,
    value_col: Optional[Union[str, List[str]]] = None,
    maxsample: Optional[int] = 30,
) -> pd.DataFrame:
    """Split multi-valued cells into separate columns (row-wise atomization).

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to atomize.
    atm_cols : str or list of str, optional
        Columns containing delimited values.
    delimiter : str, optional
        The delimiter to split on.
    value_col : str or list of str, optional
        Specific column to decompose.  ``None`` triggers auto-detection
        from *atm_cols*.
    maxsample : int, optional
        Number of sample rows used for delimiter-count mode detection.

    Returns
    -------
    pd.DataFrame
        The atomized DataFrame.
    """
    # Auto-detect candidate columns
    if not value_col:
        candidate_cols = []
        for col in atm_cols:
            sample_values = df[col].dropna().astype(str).head(maxsample)
            if sample_values.empty:
                continue
            delim_counts = sample_values.map(lambda x: x.count(delimiter))
            if delim_counts.empty:
                continue
            mode_count = delim_counts.mode().iloc[0]
            mode_ratio = (delim_counts == mode_count).mean()

            if mode_ratio >= 0.9 and mode_count > 0:
                candidate_cols.append((col, mode_count + 1))

        if not candidate_cols:
            raise ValueError("No candidate column found for row-wise atomization.")

        atom_col, num_fields = candidate_cols[0]
    else:
        atom_col = value_col[0] if isinstance(value_col, list) else value_col
        num_fields = None

    # Perform row-wise atomization
    new_rows = []

    for _, row in df.iterrows():
        cell = str(row[atom_col]) if pd.notna(row[atom_col]) else ""
        tokens = cell.split(delimiter)
        if num_fields and len(tokens) != num_fields:
            continue  # skip mismatched rows

        new_row = row.drop(labels=atom_col).to_dict()
        for i, token in enumerate(tokens):
            new_row[f"{atom_col}_{i + 1}"] = token.strip()
        new_rows.append(new_row)

    return pd.DataFrame(new_rows)
