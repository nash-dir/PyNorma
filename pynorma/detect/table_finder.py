import pandas as pd
import numpy as np
from pynorma.detect.header_finder import detect_header_end_row 

def _find_table_by_projection(df: pd.DataFrame, row_threshold_ratio: float = 0.3, col_threshold_ratio: float = 0.3) -> tuple:
    """프로젝션 프로파일 분석으로 데이터프레임 내의 주요 테이블 영역을 찾습니다."""
    if df.empty:
        return 0, 0, 0, 0
    binary_matrix = df.notna().astype(int)
    row_threshold = max(1, int(binary_matrix.shape[1] * row_threshold_ratio))
    horizontal_projection = binary_matrix.sum(axis=1)
    valid_rows = np.where(horizontal_projection >= row_threshold)[0]
    if len(valid_rows) == 0: return 0, 0, 0, 0
    top, bottom = valid_rows[0], valid_rows[-1] + 1
    col_threshold = max(1, int(binary_matrix.shape[0] * col_threshold_ratio))
    vertical_projection = binary_matrix.iloc[top:bottom].sum(axis=0)
    valid_cols = np.where(vertical_projection >= col_threshold)[0]
    if len(valid_cols) == 0: return 0, 0, 0, 0
    left, right = valid_cols[0], valid_cols[-1] + 1
    return top, left, bottom, right


def find_robust_table_area(df: pd.DataFrame) -> tuple:
    """프로젝션과 헤더 분석을 결합하여 테이블 영역을 더욱 견고하게 탐지합니다."""
    top, left, bottom, right = _find_table_by_projection(df)
    if bottom == 0 and right == 0: return 0, 0, 0, 0
    df_primary_trim = df.iloc[top:bottom, left:right]
    header_end_row_relative = detect_header_end_row(df_primary_trim)
    if header_end_row_relative == -1: return top, left, bottom, right
    df_header = df_primary_trim.iloc[:header_end_row_relative + 1]
    header_binary = df_header.notna().astype(int)
    header_vertical_proj = header_binary.sum(axis=0)
    valid_header_cols = np.where(header_vertical_proj > 0)[0]
    if len(valid_header_cols) > 0:
        header_based_right_relative = valid_header_cols[-1] + 1
        current_width = right - left
        if header_based_right_relative > current_width:
            right = left + header_based_right_relative
    return top, left, bottom, right
