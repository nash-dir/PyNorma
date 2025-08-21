import pandas as pd
from typing import List, Tuple, Union

def load_clarify_dictionary(path: str) -> List[Tuple[str, str, float]]:
    """
    (개선) Clarification dictionary를 Pandas melt를 사용해 효율적으로 로드합니다.
    """
    df = pd.read_csv(path, dtype=str)
    
    # 'target', 'addno'를 제외한 모든 컬럼을 'source'로 간주
    source_cols = df.columns[2:]
    
    # melt를 사용하여 'wide' 포맷을 'long' 포맷으로 변환
    df_long = df.melt(
        id_vars=['target', 'addno'],
        value_vars=source_cols,
        value_name='source'
    )
    
    # 실제 source 값이 없는 행(NaN)과 불필요한 컬럼 삭제
    df_long.dropna(subset=['source'], inplace=True)
    df_long.drop(columns=['variable'], inplace=True)

    # 최종 mapping 리스트 생성
    df_long['addno'] = pd.to_numeric(df_long['addno'])
    mapping = [
        (str(row['source']).strip(), str(row['target']).strip(), float(row['addno']))
        for _, row in df_long.iterrows() # 이 부분은 최종 변환이라 성능 영향이 적음
    ]
    
    return mapping


def apply_clarify_mapping(
    df: pd.DataFrame,
    column: str,
    mapping: List[Tuple[str, str, float]],
    addno_col: str = "clarify_addno",
) -> pd.DataFrame:
    """
    (개선) Pandas의 map 메서드를 사용하여 Clarification mapping을 빠르게 적용합니다.
    """
    df = df.copy()

    # 빠른 조회를 위해 mapping list를 dictionary로 변환
    source_to_target = {s: t for s, t, a in mapping}
    source_to_addno = {s: a for s, t, a in mapping}

    # 원본 컬럼의 값을 str로 변환하고 공백 제거
    original_values = df[column].astype(str).str.strip()

    # map을 사용하여 새로운 값으로 변환, 일치하는 값이 없으면 원본 값 유지
    df[column] = original_values.map(source_to_target).fillna(original_values)
    
    # addno 값도 동일한 방식으로 적용, 일치하는 값이 없으면 기본값 1
    df[addno_col] = original_values.map(source_to_addno).fillna(1.0)
    
    return df

def _merge_rows_fast(df: pd.DataFrame, key_cols: List[str], sum_columns: List[str]) -> pd.DataFrame:
    """
    (핵심 개선) Pandas의 고성능 groupby.agg를 사용하여 행을 병합합니다.
    """
    if not key_cols: # 그룹화할 키가 없으면 전체 합산
        return pd.DataFrame(df[sum_columns].sum()).T

    agg_dict = {col: 'sum' for col in sum_columns}
    
    merged_df = df.groupby(key_cols, as_index=False).agg(agg_dict)
    
    return merged_df

def clarify(
    df: pd.DataFrame,
    column: str,
    dict_path: str,
    sum_columns: Union[List[str], None] = None,
    addno_col: str = "clarify_addno",
) -> pd.DataFrame:
    """
    사전 파일을 기반으로 DataFrame의 특정 열을 정제하고, 필요시 중복 행을 병합합니다.
    """
    mapping = load_clarify_dictionary(dict_path)
    df = apply_clarify_mapping(df, column, mapping, addno_col=addno_col)

    if sum_columns:
        df = df.copy()
        
        # addno 값을 sum_columns에 곱해줌 (가중치 적용)
        for col in sum_columns:
            # 연산을 위해 숫자 타입으로 변환, 변환 불가 시 0으로 처리
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            df[addno_col] = pd.to_numeric(df[addno_col], errors='coerce').fillna(0)
            df[col] = df[col] * df[addno_col]

        # 그룹화할 기준이 될 key 컬럼들을 정의
        sum_cols_set = set(sum_columns)
        key_cols = [col for col in df.columns if col not in sum_cols_set and col != addno_col]

        # 성능이 개선된 merge 함수 호출
        df = _merge_rows_fast(df, key_cols, sum_columns)

    # 임시로 사용된 addno 컬럼이 있다면 삭제
    if addno_col in df.columns:
        df.drop(columns=[addno_col], inplace=True)

    return df