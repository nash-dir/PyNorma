import pandas as pd
from typing import Tuple

def _get_row_type_signature(row: pd.Series) -> Tuple[str, ...]:
    """DataFrame의 한 행(row)을 받아 각 셀의 타입으로 구성된 시그니처를 생성합니다."""
    types = []
    for value in row:
        if pd.isna(value) or str(value).strip() == '':
            types.append('empty')
        else:
            try:
                # 정수인지 먼저 확인하여 '1.0' 같은 실수를 숫자로 오인하는 것을 방지
                if str(value).isdigit():
                    types.append('numeric')
                else:
                    float(value)
                    types.append('numeric')
            except (ValueError, TypeError):
                types.append('string')
    return tuple(types)

def detect_header_end_row(df: pd.DataFrame, max_search_rows: int = 20) -> int:
    """
    (Legacy 로직 개선) 연속된 행들의 데이터 타입 시그니처 변화를 분석하여
    가장 큰 변화가 일어나는 지점을 헤더의 끝(마지막 주석 행)으로 탐지합니다.

    Args:
        df (pd.DataFrame): 탐색할 데이터프레임.
        max_search_rows (int): 헤더를 탐색할 최대 행 수.

    Returns:
        int: 마지막 주석 행의 인덱스. 찾지 못하면 -1을 반환합니다.
    """
    if len(df) < 2:
        return -1

    search_range = min(len(df) - 1, max_search_rows)
    signatures = [_get_row_type_signature(df.iloc[i]) for i in range(search_range + 1)]

    max_diff = -1
    header_end_index = -1

    # 연속된 두 행의 타입 시그니처를 비교합니다.
    for i in range(1,search_range):
        sig1 = signatures[i]
        sig2 = signatures[i+1]
        
        # 타입이 다른 셀의 개수를 계산합니다.
        diff_count = sum(1 for t1, t2 in zip(sig1, sig2) if t1 != t2)
        
        # 변화량이 가장 큰 지점을 헤더의 끝으로 기록합니다.
        # 단, 현재 행이 대부분 숫자로만 이루어진 경우는 주석일 확률이 높으므로 건너뜁니다.
        is_mostly_numeric = sig1.count('numeric') / len(sig1) > 0.8
        
        if diff_count > max_diff and not is_mostly_numeric:
            max_diff = diff_count
            header_end_index = i
            
    # 신뢰도 체크: 변화량이 최소 2 이상이어야 유의미한 경계로 판단
    if max_diff >= 2:
        return header_end_index
    else:
        # 변화가 거의 없다면, 첫 줄이 헤더일 가능성을 확인
        if signatures and signatures[0].count('string') / len(signatures[0]) > 0.6:
            return 0 # 첫 줄이 헤더인 경우
        return -1
