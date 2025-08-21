import pandas as pd
from typing import List, Optional, Union
from .. import config


def detect_feature_delimiter(series: pd.Series,
                             candidates: Optional[List[str]] = None
                             ) -> Optional[str]:
    """Detects the delimiter of a series.

    Parameters
    ----------
    series : pd.Series
        The series to detect the delimiter of.
    candidates : Optional[List[str]], optional
        A list of candidate delimiters, by default None

    Returns
    -------
    Optional[str]
        The detected delimiter, or None if no delimiter is detected.
    """
    if candidates is None:
        candidates = config.get_delimiters()

    total = len(series)
    best_delim = None
    max_score = 0

    for delim in candidates:
        count = series.dropna().astype(str).apply(
            lambda x: len(x.split(delim)) > 1
            ).sum()
        score = count / total
        if score > max_score:
            max_score = score
            best_delim = delim

    return best_delim if max_score > 0.1 else None


def atomize_by_column(
    df: pd.DataFrame,
    atm_cols: Optional[Union[str, List[str]]] = None,
    delimiter: Optional[str] = None
) -> pd.DataFrame:
    """Atomizes a DataFrame by column.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to atomize.
    atm_cols : Optional[Union[str, List[str]]], optional
        The columns to atomize, by default None
    delimiter : Optional[str], optional
        The delimiter to use, by default None

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
            continue  # Skip if delimiter is not found
        df[col] = df[col].astype(str).str.split(this_delim)
        df[col] = df[col].apply(lambda x:
                                [i.strip() for i in x if i.strip() != ""])
        df = df.explode(col).reset_index(drop=True)

    return df


def atomize_by_row(
    df: pd.DataFrame,
    atm_cols: Optional[Union[str, List[str]]] = None,
    delimiter: Optional[str] = None,
    value_col: Optional[Union[str, List[str]]] = None,
    maxsample: Optional[int] = 30
) -> pd.DataFrame:
    """Atomizes a DataFrame by row.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to atomize.
    atm_cols : Optional[Union[str, List[str]]], optional
        The columns to atomize, by default None
    delimiter : Optional[str], optional
        The delimiter to use, by default None
    value_col : Optional[Union[str, List[str]]], optional
        The value column, by default None
    maxsample : Optional[int], optional
        The maximum number of samples to use, by default 30

    Returns
    -------
    pd.DataFrame
        The atomized DataFrame.
    """
    # 자동 탐지를 위한 기본 설정
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
                candidate_cols.append((col, mode_count + 1))  # delimiter + 1

        if not candidate_cols:
            raise ValueError("No candidate column found for row-wise atomize.")

        # 분해 열 리스트 구성: 가장 첫 번째 후보 기준
        atom_col, num_fields = candidate_cols[0]
    else:
        atom_col = value_col[0] if isinstance(value_col, list) else value_col
        num_fields = None  # 분해 수는 이후 분해 시점에서 유추

    # row-wise atomize 수행
    new_rows = []
    
    for _, row in df.iterrows():
        cell = str(row[atom_col]) if pd.notna(row[atom_col]) else ""
        tokens = cell.split(delimiter)
        if num_fields and len(tokens) != num_fields:
            continue  # 불일치하는 행은 건너뜀

        new_row = row.drop(labels=atom_col).to_dict()
        for i, token in enumerate(tokens):
            new_row[f"{atom_col}_{i+1}"] = token.strip()
        new_rows.append(new_row)

    return pd.DataFrame(new_rows)
