import pandas as pd
import numpy as np
from typing import List, Tuple, Dict

def _get_row_type_signature(row: pd.Series) -> Tuple[str, ...]:
    """
    DataFrame의 한 행(row)을 받아 각 셀의 타입으로 구성된 시그니처를 생성합니다.
    셀 타입: 'numeric', 'string', 'empty'
    """
    types = []
    for value in row:
        if pd.isna(value) or str(value).strip() == '':
            types.append('empty')
        else:
            try:
                float(value)
                types.append('numeric')
            except (ValueError, TypeError):
                types.append('string')
    return tuple(types)


def _calculate_scores_for_row(
    row_index: int,
    signatures: List[Tuple[str, ...]],
    stability_window: int = 3
) -> Dict[str, float]:
    """
    특정 행에 대해 '데이터다움(data-likeness)' 점수를 계산합니다.
    점수는 안정성, 숫자 밀도, 채움 비율 세 가지 지표로 구성됩니다.
    """
    target_index = row_index + 1
    if target_index >= len(signatures):
        return {'stability': 0, 'numeric': 0, 'fill_rate': 0}

    target_signature = signatures[target_index]
    num_cols = len(target_signature)
    if num_cols == 0:
        return {'stability': 0, 'numeric': 0, 'fill_rate': 0}

    # 1. 안정성(Stability) 점수: 다음 N개 행의 타입 패턴이 얼마나 일치하는가
    stable_matches = 0
    for i in range(1, stability_window):
        compare_index = target_index + i
        if compare_index < len(signatures) and signatures[compare_index] == target_signature:
            stable_matches += 1
    stability_score = stable_matches / (stability_window - 1) if stability_window > 1 else 1.0

    # 2. 숫자 밀도(Numeric Density) 점수: 행에 숫자 타입이 얼마나 있는가
    numeric_score = target_signature.count('numeric') / num_cols

    # 3. 채움 비율(Fill Rate) 점수: 행에 비어있지 않은 셀이 얼마나 있는가
    fill_rate_score = (num_cols - target_signature.count('empty')) / num_cols
    
    return {
        'stability': stability_score,
        'numeric': numeric_score,
        'fill_rate': fill_rate_score
    }


def _find_best_header_boundary(scores: List[float]) -> int:
    """점수 리스트를 분석하여 헤더와 데이터의 경계를 나타내는 최적의 인덱스를 찾습니다."""
    if len(scores) < 2:
        return -1
        
    scores_arr = np.array(scores)
    jumps = np.diff(scores_arr) # 각 행 사이의 점수 변화량(jump)

    # 점수가 크게 상승하면서, 도달한 점수 자체도 높은 곳에 가중치를 부여
    weighted_jumps = jumps * scores_arr[1:]
    best_index = np.argmax(weighted_jumps)
    
    return int(best_index)


def detect_header_end_row(
    df: pd.DataFrame, 
    max_search_rows: int = 30
) -> int:
    """
    여러 휴리스틱을 종합한 점수 시스템을 기반으로 헤더의 마지막 행 인덱스를 탐지합니다.

    Args:
        df (pd.DataFrame): 탐색할 데이터프레임.
        max_search_rows (int, optional): 헤더를 탐색할 최대 행 수. 기본값은 30입니다.

    Returns:
        int: 헤더의 마지막 행 인덱스. 헤더를 찾지 못한 경우 -1을 반환합니다.
    """
    search_range = min(len(df), max_search_rows)
    if search_range < 3:
        return -1

    # 1. 모든 행의 타입 시그니처를 미리 계산하여 성능 향상
    signatures = [_get_row_type_signature(df.iloc[i]) for i in range(search_range)]

    # 2. 각 행에 대해 '데이터다움' 점수 계산
    total_scores = []
    weights = {'stability': 0.5, 'numeric': 0.4, 'fill_rate': 0.1}
    
    for i in range(search_range - 1):
        scores = _calculate_scores_for_row(i, signatures)
        total_score = (scores['stability'] * weights['stability'] +
                       scores['numeric'] * weights['numeric'] +
                       scores['fill_rate'] * weights['fill_rate'])
        total_scores.append(total_score)

    if not total_scores:
        return -1

    # 3. 점수 변화를 분석하여 최적의 경계선 결정
    header_end_index = _find_best_header_boundary(total_scores)

    # 4. 신뢰도 확인: 데이터 영역의 점수가 특정 임계값(e.g., 0.5)을 넘어야 유효한 경계로 인정
    if total_scores[header_end_index + 1] > 0.5:
        return header_end_index
    else:
        return -1