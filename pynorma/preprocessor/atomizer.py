"""Atomizer — split multi-valued cells into separate rows or columns.

Includes two detection methods:
  - detect_feature_delimiter: proportion-based delimiter detection (original)
  - detect_multivalue_columns: overlap-ratio based 1NF violation detection (new)
"""

import logging
from collections import Counter
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd

from .. import config

logger = logging.getLogger("pynorma")

# Default in-cell delimiter candidates
INTRA_CELL_DELIMITERS = [",", ";", "/", "|"]


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


def detect_multivalue_columns(
    df: pd.DataFrame,
    candidates: Optional[List[str]] = None,
    *,
    min_overlap: float = 0.3,
    min_multi_ratio: float = 0.1,
) -> List[Tuple[str, str, float]]:
    """Detect columns violating 1NF using atom overlap ratio.

    For each column, tries candidate in-cell delimiters. If splitting
    produces atoms that re-appear across other cells in the same column,
    the column is flagged as multi-valued.

    The key insight: correct splitting produces atoms that overlap with
    single-valued cells. Wrong splitting produces unique fragments.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to analyse.
    candidates : list of str, optional
        In-cell delimiter candidates. Defaults to ``,;/|``.
    min_overlap : float
        Minimum overlap ratio to flag a column (0~1).
    min_multi_ratio : float
        Minimum proportion of cells that must contain > 1 atom.

    Returns
    -------
    list of (column_name, delimiter, overlap_ratio)
        Sorted by overlap_ratio descending. Only columns above threshold.

    Examples
    --------
    >>> df = pd.DataFrame({
    ...     "Name": ["Alice", "Bob", "Charlie"],
    ...     "Fruits": ["apple", "apple, banana", "apple, banana, carrot"],
    ... })
    >>> detect_multivalue_columns(df)
    [('Fruits', ',', 0.857)]
    """
    if candidates is None:
        candidates = INTRA_CELL_DELIMITERS

    results = []

    for col in df.columns:
        series = df[col].dropna().astype(str)
        if series.empty or len(series) < 3:
            continue

        best_delim = None
        best_overlap = 0.0

        for delim in candidates:
            # Split all cells by this delimiter
            split_cells = series.apply(lambda x, d=delim: [s.strip() for s in x.split(d) if s.strip()])

            # Count cells with multiple atoms
            multi_mask = split_cells.apply(len) > 1
            multi_ratio = multi_mask.mean()

            if multi_ratio < min_multi_ratio:
                continue

            # Collect all individual atoms
            all_atoms = Counter()
            for atoms in split_cells:
                for a in atoms:
                    all_atoms[a] += 1

            if not all_atoms:
                continue

            # Overlap: atoms from multi-valued cells that appear in other cells
            # (as single values or in other multi-valued cells)
            multi_atoms = set()
            for atoms in split_cells[multi_mask]:
                multi_atoms.update(atoms)

            single_atoms = set()
            for atoms in split_cells[~multi_mask]:
                single_atoms.update(atoms)

            if not multi_atoms:
                continue

            # Overlap = proportion of multi-cell atoms that also appear elsewhere
            # Also count atoms that appear in > 1 multi-valued cell
            overlap_count = 0
            for atom in multi_atoms:
                if atom in single_atoms or all_atoms[atom] > 1:
                    overlap_count += 1

            overlap_ratio = overlap_count / len(multi_atoms)

            if overlap_ratio > best_overlap:
                best_overlap = overlap_ratio
                best_delim = delim

        if best_delim and best_overlap >= min_overlap:
            results.append((col, best_delim, round(best_overlap, 3)))

    # Sort by overlap descending
    results.sort(key=lambda x: x[2], reverse=True)
    return results


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
