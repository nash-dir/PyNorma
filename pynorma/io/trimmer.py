# pynorma/preprocessor/trimmer.py

import pandas as pd
import numpy as np
from typing import Union, Literal, Dict, List, Tuple
from pynorma.detect.header_finder import detect_header_end_row
from pynorma.detect.table_finder import find_robust_table_area


def trim_dataframe(
    df: pd.DataFrame,
    trim_mode: Union[bool, Literal["auto"], dict] = "auto",
    set_header: bool = True
) -> pd.DataFrame:
    """
    데이터프레임의 불필요한 영역을 잘라내고, 헤더를 올바르게 설정합니다.

    Args:
        df (pd.DataFrame): 원본 데이터프레임.
        trim_mode (Union[bool, Literal["auto"], dict], optional):
            - "auto": 데이터 영역을 자동으로 탐지하여 잘라냅니다.
            - dict: {'top': y1, 'bottom': y2, 'left': x1, 'right': x2} 좌표를 직접 지정합니다.
            - False: 트림을 수행하지 않습니다.
            기본값은 "auto"입니다.
        set_header (bool, optional): True일 경우, 잘라낸 후 헤더를 자동으로
            탐지하고 설정합니다. 기본값은 True입니다.

    Returns:
        pd.DataFrame: 트림과 헤더 설정이 완료된 데이터프레임.
    """
    if not trim_mode:
        df_trimmed = df.copy()
    elif trim_mode == "auto":
        top, left, bottom, right = find_robust_table_area(df)
        if bottom == 0 and right == 0:
            return df
        df_trimmed = df.iloc[top:bottom, left:right].reset_index(drop=True)
    elif isinstance(trim_mode, dict):
        top = trim_mode.get("top", 0)
        bottom = trim_mode.get("bottom", df.shape[0])
        left = trim_mode.get("left", 0)
        right = trim_mode.get("right", df.shape[1])
        df_trimmed = df.iloc[top:bottom, left:right].reset_index(drop=True)
    else:
        raise ValueError("The 'trim' argument must be 'auto', False, or a dict.")

    if set_header and not df_trimmed.empty:
        header_end_row = detect_header_end_row(df_trimmed)
        if header_end_row != -1:
            df_trimmed.columns = df_trimmed.iloc[header_end_row]
            df_trimmed = df_trimmed.iloc[header_end_row + 1:].reset_index(drop=True)

    return df_trimmed
