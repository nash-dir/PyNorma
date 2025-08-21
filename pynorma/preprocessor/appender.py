
import pandas as pd
from typing import Union, Literal, Dict, Optional

def isthere_header(df: pd.DataFrame) -> bool:
    """Checks if a DataFrame has a header.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to check.

    Returns
    -------
    bool
        Whether the DataFrame has a header.
    """
    cols = df.shape[1]

    # Case 1: feature names are : 0, 1, 2, ..., (cols-1)
    is_integer_index = list(df.columns) == list(range(cols))

    # Case 2: feature names are : 'Unnamed: 0', 'Unnamed: 1', ..., 'Unnamed: (cols-1)'
    is_unnamed_index = list(df.columns) == [f'Unnamed: {i}' for i in range(cols)]

    return is_integer_index or is_unnamed_index

def append(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    strict: bool = False,
    recover_types: bool = False,
    verbose: bool = False,
    df2_header: Union[bool, Literal["auto"], dict] = "auto",
) -> Optional[pd.DataFrame]:
    """Appends two DataFrames.

    Parameters
    ----------
    df1 : pd.DataFrame
        The first DataFrame.
    df2 : pd.DataFrame
        The second DataFrame.
    strict : bool, optional
        Whether to use strict mode, by default False
    recover_types : bool, optional
        Whether to recover types, by default False
    verbose : bool, optional
        Whether to print verbose output, by default False
    df2_header : Union[bool, Literal["auto"], dict], optional
        Whether df2 has a header, by default "auto"

    Returns
    -------
    Optional[pd.DataFrame]
        The appended DataFrame, or None if the column counts do not match.
    """
    
    # Step 1: auto-detect header if needed
    if df2_header == "auto":
        df2_header = isthere_header(df2)

    # Step 2: if df2 has no header, use shape-based concatenation
    if df2_header is False:
        if df1.shape[1] == df2.shape[1]:
            result = pd.concat([df1, df2], ignore_index=True)
            if verbose:
                print("[Append] Concatenated without header matching (shape-only).")
            return result
        else:
            print("[Error] Column count mismatch between df1 and df2.")
            print(f"df1.shape[1] = {df1.shape[1]}, df2.shape[1] = {df2.shape[1]}")
            return None
   
    # 1. Check column consistency
    structure = compare_structure(df1, df2)

    if verbose:
        print("[Append] Structure diff:", structure)

    if strict and (structure["missing_in_df2"] or structure["extra_in_df2"] or structure["dtype_mismatch"]):
        raise ValueError("DataFrame structure mismatch: strict mode enabled.")
    
    # 2. Fix column order based on df1
    common_cols = df1.columns.intersection(df2.columns)
    df2 = df2.reindex(columns=df1.columns, fill_value=pd.NA)

    # 3. Recover types
    if recover_types:
        for col in common_cols:
            dtype1 = df1[col].dtype
            try:
                df2[col] = df2[col].astype(dtype1)
            except Exception:
                if verbose:
                    print(f"[Append] Failed to cast df2[{col}] to {dtype1}, keeping original dtype {df2[col].dtype}")

    # 4. Execute append
    result = pd.concat([df1, df2], ignore_index=True)
    return result

def compare_structure(df1: pd.DataFrame, df2: pd.DataFrame) -> Dict[str, object]:
    """Compares the structure of two DataFrames.

    Parameters
    ----------
    df1 : pd.DataFrame
        The first DataFrame.
    df2 : pd.DataFrame
        The second DataFrame.

    Returns
    -------
    Dict[str, object]
        A dictionary containing the structural differences between the two DataFrames.
    """
    cols1 = set(df1.columns)
    cols2 = set(df2.columns)
    
    missing_in_df2 = list(cols1 - cols2)
    extra_in_df2 = list(cols2 - cols1)

    dtype_mismatch = {}
    for col in cols1 & cols2:
        if df1[col].dtype != df2[col].dtype:
            dtype_mismatch[col] = (str(df1[col].dtype), str(df2[col].dtype))

    return {
        "missing_in_df2": missing_in_df2,
        "extra_in_df2": extra_in_df2,
        "dtype_mismatch": dtype_mismatch
    }

