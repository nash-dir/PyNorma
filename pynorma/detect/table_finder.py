import pandas as pd
import numpy as np
from pynorma.detect.header_finder import detect_header_end_row 
from typing import List, Tuple

def _find_table_by_projection(df: pd.DataFrame) -> tuple:
    """프로젝션 방식으로 테이블의 전체적인 범위를 너그럽게 추정합니다."""
    if df.empty:
        return 0, 0, 0, 0

    df_cleaned = df.replace(r'^\s*$', pd.NA, regex=True)
    binary_matrix = df_cleaned.notna().astype(int)
    
    horizontal_projection = binary_matrix.sum(axis=1)
    
    if horizontal_projection.empty or horizontal_projection.max() == 0:
        return 0, 0, 0, 0
        
    # 데이터가 가장 꽉 찬 행의 50% 이상 채워진 행만 유효한 것으로 간주
    row_threshold = max(1, int(horizontal_projection.max() * 0.5))
    valid_rows = np.where(horizontal_projection >= row_threshold)[0]
    
    if len(valid_rows) == 0:
        return 0, 0, 0, 0
    
    top = valid_rows[0]
    bottom = valid_rows[-1] + 1
    
    # 해당 행 범위 내에서, 값이 하나라도 있는 모든 열을 포함하여 너비를 확보
    vertical_projection = binary_matrix.iloc[top:bottom].sum(axis=0)
    valid_cols = np.where(vertical_projection > 0)[0]
    
    if len(valid_cols) == 0: 
        return 0, 0, 0, 0
        
    left = valid_cols[0]
    right = valid_cols[-1] + 1
    
    return top, left, bottom, right

def find_robust_table_area(df: pd.DataFrame) -> tuple:
    """
    프로젝션으로 전체 범위를 잡고, 헤더 탐지로 시작점을 정밀하게 찾는 하이브리드 방식입니다.
    """
    # 1. 프로젝션 방식으로 테이블의 최대 범위를 너그럽게 추정합니다.
    #    이 단계에서 열이 잘려나가는 문제를 방지합니다.
    top_p, left_p, bottom_p, right_p = _find_table_by_projection(df)

    if bottom_p == 0 and right_p == 0: 
        return 0, 0, 0, 0
    
    # 2. 추정된 영역 내에서 헤더의 끝 위치를 정밀하게 탐지합니다.
    df_candidate = df.iloc[top_p:bottom_p, left_p:right_p]
    header_end_row_relative = detect_header_end_row(df_candidate)
    
    # 3. 헤더 탐지 결과를 바탕으로 최종 테이블 영역을 확정합니다.
    if header_end_row_relative != -1:
        # 헤더 탐지에 성공한 경우:
        # - top: 헤더의 시작 위치를 기준으로 정확하게 설정하여 주석을 제거합니다.
        #        (detect_header_end_row는 마지막 헤더 행의 인덱스를 반환하므로,
        #         실제 데이터는 그 다음 행부터 시작하지만, trimmer가 헤더를 포함한
        #         블록을 받아야 하므로 header_end_row_relative를 그대로 더합니다.)
        #         다만, townbusiness1.csv의 경우 헤더가 한 줄이므로,
        #         detect_header_end_row가 헤더 이전 줄을 반환해야 올바른 top이 설정됩니다.
        #         따라서 +1을 하여 헤더 줄 자체를 top으로 만듭니다.
        #         (이 부분은 detect_header_end_row의 반환 값 정의에 따라 조절 필요)
        #         현재 로직상으로는 header_end_row_relative가 마지막 헤더 행이므로,
        #         top은 top_p + header_end_row_relative가 되어야 합니다.
        #         townbusiness1.csv의 경우, 헤더 이전의 '1,2,3,4' 행이 헤더로 인식되는 문제를 해결해야 합니다.
        #         가장 확실한 방법은, 헤더 탐지 후 그 헤더를 기준으로 다시 left, right를 정하는 것입니다.

        # 헤더의 절대 위치 계산
        # detect_header_end_row가 마지막 헤더의 상대 인덱스를 반환한다고 가정
        # townbusiness1.csv의 경우, 'County...' 행이 헤더이므로 이 행의 인덱스를 찾아야 함
        # 현재 detect_header_end_row가 '1,2,3,4'를 헤더로 볼 수 있음 -> 이 부분을 수정해야 함
        # 임시 수정: 헤더 탐지 후, 그 헤더를 기준으로 left, right를 다시 계산
        
        final_top = top_p + header_end_row_relative
        
        # 헤더 행을 기준으로 left, right를 다시 계산하여 정확도 향상
        header_series = df.iloc[final_top].replace(r'^\s*$', pd.NA, regex=True)
        valid_header_indices = header_series.notna().to_numpy().nonzero()[0]
        
        if len(valid_header_indices) > 0:
            final_left = valid_header_indices[0]
            final_right = valid_header_indices[-1] + 1
            return final_top, final_left, bottom_p, final_right
        else:
            # 헤더가 비어있으면 프로젝션 결과를 그대로 사용
            return top_p, left_p, bottom_p, right_p

    else:
        # 헤더 탐지에 실패한 경우, 프로젝션 결과만으로 반환합니다.
        return top_p, left_p, bottom_p, right_p
