# pynorma/preprocessor/trimmer.py

import pandas as pd
from typing import Union, Literal, Optional, Tuple, Dict

# trimmer는 이제 헤더 탐지 기능도 직접 사용합니다.
from pynorma.detect.table_finder import find_robust_table_area
from pynorma.detect.header_finder import detect_header_end_row

def trim_dataframe(
    df: pd.DataFrame,
    trim_mode: Union[bool, Literal["auto"], dict] = "auto",
    set_header: bool = True,
    header_row: Optional[int] = None
) -> Tuple[pd.DataFrame, Dict]:
    """
    데이터프레임의 불필요한 영역을 잘라내고, 결과물과 처리 정보를 함께 반환합니다.
    """
    df_trimmed = df.copy()
    original_shape = df.shape
    
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
        pass
    else:
        raise ValueError("The 'trim' argument must be 'auto', False, or a dict.")

    # 2. 결정된 헤더 위치를 기준으로 헤더를 설정합니다.
    final_header_row_abs = header_row # 최종 사용된 절대 헤더 위치를 기록하기 위한 변수
    
    if set_header and not df_trimmed.empty:
        header_to_set = header_row # 실제로 사용할 헤더 위치

        # --- ✨ 핵심 수정: header_row가 None일 때 자동 탐지 로직 추가 ---
        if header_to_set is None:
            # 외부에서 헤더 위치를 지정해주지 않았다면, 잘라낸 df를 기준으로 직접 탐지합니다.
            last_comment_row = detect_header_end_row(df_trimmed)
            if last_comment_row != -1:
                # 실제 헤더는 마지막 주석 다음 행입니다. (상대 좌표)
                # 이 값을 바로 헤더 설정에 사용합니다.
                header_to_set = last_comment_row + 1
                # 절대 좌표도 기록해 둡니다.
                final_header_row_abs = top_offset + header_to_set
        
        # --- ✨ 핵심 수정: 헤더 설정 로직 통합 ---
        # 유효한 헤더 위치가 결정되었을 경우에만 헤더를 설정합니다.
        if header_to_set is not None:
            # header_row가 외부에서 주어졌다면 절대 좌표이므로 상대 좌표로 변환
            # 내부에서 탐지했다면 이미 상대 좌표이므로 변환 불필요
            if header_row is not None:
                 header_row_relative = header_to_set - top_offset
            else:
                 header_row_relative = header_to_set

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
        'header_row_abs': final_header_row_abs # 최종 사용된 헤더 위치를 보고
    }
    
    return df_trimmed, trim_info
