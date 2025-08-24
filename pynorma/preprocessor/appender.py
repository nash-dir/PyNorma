import pandas as pd
from typing import Union, Literal, Dict, Optional, Any

def isthere_header(df: pd.DataFrame) -> bool:
    """Checks if a DataFrame has a header. Returns True if a header exists."""
    if df.empty:
        return False
    cols = df.shape[1]
    is_integer_index = list(df.columns) == list(range(cols))
    is_unnamed_index = all(isinstance(c, str) and c.startswith('Unnamed:') for c in df.columns)
    return not (is_integer_index or is_unnamed_index)

def append(
    df1: Any,
    df2: Any,
    strict: bool = False,
    recover_types: bool = False,
    verbose: bool = False,
    df2_header: Union[bool, Literal["auto"]] = "auto",
) -> Optional[pd.DataFrame]:
    """
    두 개의 데이터프레임(또는 파서가 반환한 튜플)을 병합합니다.
    """
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
            print("[Append] Structure diff:", structure)
        if strict and (structure["missing_in_df2"] or structure["extra_in_df2"] or structure["dtype_mismatch"]):
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
                        print(f"[Append] Failed to cast df2['{col}'] to {dtype1}")
        
        result = pd.concat([df1, df2_reindexed], ignore_index=True)

    else: # df2에 헤더가 없는 경우
        # --- ✨ 핵심 수정: 열 개수가 달라도 df1을 기준으로 df2를 조절 ---
        num_cols_df1 = df1.shape[1]
        num_cols_df2 = df2.shape[1]

        if num_cols_df1 != num_cols_df2:
            if verbose:
                print(f"[Append Warning] Column count mismatch in no-header mode. "
                      f"Adjusting df2 from {num_cols_df2} to {num_cols_df1} columns.")
            
            if num_cols_df2 > num_cols_df1:
                # df2의 열이 더 많으면, df1의 열 개수에 맞춰 자릅니다.
                df2 = df2.iloc[:, :num_cols_df1]
            else: # num_cols_df2 < num_cols_df1
                # df2의 열이 더 적으면, 부족한 만큼 빈 열을 추가합니다.
                for i in range(num_cols_df1 - num_cols_df2):
                    # 고유한 열 이름을 부여하여 충돌을 방지합니다.
                    df2[f'__pynorma_added_col_{i}'] = pd.NA
        
        # 이제 열 개수가 동일하므로, df1의 컬럼을 그대로 사용하여 병합합니다.
        df2.columns = df1.columns
        result = pd.concat([df1, df2], ignore_index=True)
        if verbose:
            print("[Append] Concatenated based on shape (no header in df2).")
            
    return result

def compare_structure(df1: pd.DataFrame, df2: pd.DataFrame) -> Dict[str, object]:
    """Compares the structure of two DataFrames."""
    cols1 = set(df1.columns)
    cols2 = set(df2.columns)
    
    missing_in_df2 = list(cols1 - cols2)
    extra_in_df2 = list(cols2 - cols1)

    dtype_mismatch = {}
    common_cols = cols1.intersection(cols2)
    for col in common_cols:
        if df1[col].dtype != df2[col].dtype:
            dtype_mismatch[col] = (str(df1[col].dtype), str(df2[col].dtype))

    return {
        "missing_in_df2": missing_in_df2,
        "extra_in_df2": extra_in_df2,
        "dtype_mismatch": dtype_mismatch
    }
