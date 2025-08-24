# pynorma/preprocessor/trimmer.py

import pandas as pd
from typing import Union, Literal, Optional, Tuple, Dict

# trimmer는 탐지(detect) 모듈을 호출하여 사용합니다.
from pynorma.detect.table_finder import find_robust_table_area

def trim_dataframe(
    df: pd.DataFrame,
    trim_mode: Union[bool, Literal["auto"], dict] = "auto",
    set_header: bool = True,
    header_row: Optional[int] = None
) -> Tuple[pd.DataFrame, Dict]:
    """
    데이터프레임의 불필요한 영역을 잘라내고, 결과물과 처리 정보를 함께 반환합니다.

    이 함수는 하위 파서(csv_parser 등)에 의해 호출되는 실무 모듈입니다.

    Args:
        df (pd.DataFrame): 원본 데이터프레임.
        trim_mode (Union[bool, ...]): 트림 모드.
        set_header (bool): 헤더 설정 여부.
        header_row (Optional[int]): 원본 데이터프레임 기준의 헤더 행 인덱스.

    Returns:
        Tuple[pd.DataFrame, Dict]:
            - pd.DataFrame: 전처리가 완료된 데이터프레임.
            - Dict: verbose 출력을 위한 상세 처리 정보.
    """
    df_trimmed = df.copy()
    original_shape = df.shape
    
    # 트림 좌표 초기화 (트림 안 할 경우를 대비)
    top, left, bottom, right = 0, 0, original_shape[0], original_shape[1]
    top_offset = 0

    # 1. trim_mode에 따라 테이블 영역을 잘라냅니다.
    if trim_mode == "auto":
        top, left, bottom, right = find_robust_table_area(df)
        df_trimmed = df.iloc[top:bottom, left:right].reset_index(drop=True)
        top_offset = top
    elif isinstance(trim_mode, dict):
        top = trim_mode.get("top", 0)
        bottom = trim_mode.get("bottom", original_shape[0])
        left = trim_mode.get("left", 0)
        right = trim_mode.get("right", original_shape[1])
        df_trimmed = df.iloc[top:bottom, left:right].reset_index(drop=True)
        top_offset = top
    elif trim_mode is False:
        pass # 트림을 수행하지 않습니다.
    else:
        raise ValueError("The 'trim' argument must be 'auto', False, or a dict.")

    # 2. 결정된 헤더 위치를 기준으로 헤더를 설정합니다.
    if set_header and header_row is not None and not df_trimmed.empty:
        # 절대 좌표(header_row)를 상대 좌표로 변환
        header_row_relative = header_row - top_offset
        if 0 <= header_row_relative < len(df_trimmed):
            df_trimmed.columns = df_trimmed.iloc[header_row_relative]
            df_trimmed = df_trimmed.iloc[header_row_relative + 1:].reset_index(drop=True)

    # 3. verbose 출력을 위한 상세 정보를 dict로 묶어 반환합니다.
    trim_info = {
        'original_shape': original_shape,
        'trimmed_shape': df_trimmed.shape,
        'top': top,
        'bottom': bottom,
        'left': left,
        'right': right,
        'header_row_abs': header_row
    }
    
    return df_trimmed, trim_info
