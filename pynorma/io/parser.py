# pynorma/parser.py

import os
import pandas as pd
from typing import Union, Literal, Optional

# 각 파일 형식에 특화된 하위 파서들을 임포트합니다.
from pynorma.io import csv_parser, xlsx_parser

def parse(
    filepath: str,
    # --- 구조 탐지 및 제어 ---
    trim: Union[bool, Literal["auto"], dict] = "auto",
    is_header: Union[bool, int] = True,
    # --- 파일 형식별 상세 옵션 ---
    delimiter: Optional[str] = None,
    sheet_name: Union[str, int, None] = None, # 기본값을 None으로 하여 자동 탐지 기능 활성화
    # --- 유틸리티 ---
    encoding: str = "auto",
    verbose: bool = False
) -> pd.DataFrame:
    """
    파일 형식을 자동으로 탐지하여 파싱하고, 지능형 전처리 기능을 적용합니다.

    이 함수는 PyNorma의 메인 API로, 사용자가 가장 먼저 호출하게 될 함수입니다.

    Args:
        filepath (str): 파싱할 파일의 경로.
        trim (Union[bool, "auto", dict], optional): 데이터 주변의 불필요한 행/열 제거 방식.
            - "auto": 테이블 영역을 지능적으로 탐지합니다. (기본값)
            - False: 트림 기능을 사용하지 않습니다.
            - dict: {'top': 5, ...} 형태로 사용자가 직접 좌표를 지정합니다.
        is_header (Union[bool, int], optional): 헤더 처리 방식.
            - True: 헤더 위치를 자동으로 탐지합니다. (기본값)
            - False: 헤더가 없는 파일로 처리합니다.
            - int: 헤더의 절대 위치를 직접 지정합니다. (예: is_header=2)
        delimiter (Optional[str], optional): [CSV 전용] CSV 파일의 구분자.
            None일 경우 Pandas가 자동으로 추정합니다. (기본값)
        sheet_name (Union[str, int, None], optional): [XLSX 전용] 읽어올 시트.
            None일 경우 데이터가 가장 많은 시트를 자동으로 탐지합니다. (기본값)
        encoding (str, optional): 파일 인코딩. "auto"일 경우 자동 탐지합니다. (기본값)
        verbose (bool, optional): True일 경우, 파싱 과정의 상세 정보를 출력합니다. (기본값: False)

    Returns:
        pd.DataFrame: 전처리가 완료된 최종 데이터프레임.
    """
    file_extension = os.path.splitext(filepath)[1].lower()

    # 1. 파일 확장자에 따라 적절한 하위 파서를 호출합니다.
    #    하위 파서는 항상 (DataFrame, info_dict) 튜플을 반환합니다.
    if file_extension == '.csv':
        df, info = csv_parser.parse_csv(
            filepath,
            trim=trim,
            is_header=is_header,
            delimiter=delimiter,
            encoding=encoding,
            verbose=verbose # verbose 플래그는 정보 생성을 위해 전달
        )
    elif file_extension in ['.xlsx', '.xls']:
        df, info = xlsx_parser.parse_xlsx(
            filepath,
            trim=trim,
            is_header=is_header,
            sheet_name=sheet_name,
            encoding=encoding,
            verbose=verbose
        )
    else:
        raise ValueError(f"Unsupported filetype: '{file_extension}'")

    # 2. verbose가 True이고, 하위 파서로부터 상세 정보(info)가 반환되었을 경우에만 출력합니다.
    if verbose and info:
        original_shape = info.get('original_shape', ('N/A', 'N/A'))
        trimmed_shape = info.get('trimmed_shape', ('N/A', 'N/A'))
        
        print("-" * 50)
        print(f"[PyNorma Verbose Output for: {os.path.basename(filepath)}]")
        print("-" * 50)
        print(f"  - File Type       : {file_extension}")
        if 'detected_sheet' in info:
            print(f"  - Detected Sheet  : '{info['detected_sheet']}'")
        print(f"  - Trim Border     : top={info.get('top')}, bottom={info.get('bottom')}, "
              f"left={info.get('left')}, right={info.get('right')}")
        print(f"  - Shape Change    : Original({original_shape[0]}R, {original_shape[1]}C) "
              f"-> Final({trimmed_shape[0]}R, {trimmed_shape[1]}C)")
        print(f"  - Header Index    : {info.get('header_row_abs')}")
        print("-" * 50)

    # 3. 최종적으로 사용자에게는 전처리된 데이터프레임만 반환합니다.
    return df
