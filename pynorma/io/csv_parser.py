# pynorma/io/csv_parser.py

import pandas as pd
from typing import Union, Literal, Optional, Tuple, Dict

# 실무를 담당할 trimmer와 각종 탐지/유틸리티 함수들을 임포트합니다.
from pynorma.io import trimmer
from ..utils import clean_dataframe, detect_encoding
from ..detect.header_finder import detect_header_end_row

def parse_csv(
    filepath: str,
    trim: Union[bool, Literal["auto"], dict] = "auto",
    is_header: Union[bool, int] = True,
    delimiter: Optional[str] = None,
    encoding: str = "auto",
    verbose: bool = False # verbose는 현재 사용되지 않지만, 인터페이스 일관성을 위해 유지
) -> Tuple[pd.DataFrame, Dict]:
    """
    CSV 파일을 파싱하고, trimmer를 호출하여 전처리를 수행한 후,
    결과물과 처리 정보를 튜플 형태로 반환합니다.

    Args:
        filepath (str): CSV 파일 경로.
        trim (Union[bool, "auto", dict]): trimmer에게 전달될 트림 모드.
        is_header (Union[bool, int]): 헤더 처리 방식.
        delimiter (Optional[str]): Pandas read_csv에 전달될 구분자.
        encoding (str): 파일 인코딩.
        verbose (bool): 상위 parser와의 인터페이스 일관성을 위한 인자.

    Returns:
        Tuple[pd.DataFrame, Dict]:
            - pd.DataFrame: 전처리가 완료된 데이터프레임.
            - Dict: verbose 출력을 위한 상세 처리 정보.
    """
    # 1. 인코딩 탐지: 'auto'일 경우 자동으로 인코딩을 찾습니다.
    file_encoding = detect_encoding(filepath) if encoding == "auto" else encoding
    
    try:
        # 2. 파일 읽기: Pandas에 의존하여 파일을 한 번만 읽습니다.
        #    - delimiter=None으로 두어 Pandas가 자동으로 탐지하도록 합니다.
        #    - header=None으로 설정하여 모든 데이터를 그대로 읽어옵니다.
        df_raw = pd.read_csv(
            filepath,
            header=None,
            dtype=str,
            encoding=file_encoding,
            delimiter=delimiter,
            on_bad_lines='warn'
        )
    except Exception as e:
        # 파일 읽기 실패 시, 사용자에게 친절한 에러 메시지를 보여줍니다.
        print(f"Error reading CSV file '{filepath}' with encoding '{file_encoding}': {e}")
        raise

    # 3. 기본적인 데이터 클리닝을 수행합니다.
    df_raw = clean_dataframe(df_raw)

    # 4. is_header 옵션에 따라 헤더의 절대 위치(header_index)를 결정합니다.
    header_index: Optional[int] = None
    if isinstance(is_header, int):
        # 사용자가 직접 정수 값을 지정한 경우
        header_index = is_header
    elif is_header is True:
        # True일 경우, 자동으로 헤더 위치를 탐지합니다.
        # header_finder는 파일 경로가 아닌 DataFrame을 받을 수 있도록 수정 필요
        # 임시로 파일 경로를 넘겨주는 detect_header_row를 사용
        # TODO: detect_header_row가 df_raw를 직접 받도록 수정
        header_index = detect_header_end_row(df_raw) # df_raw를 직접 분석
        if header_index == -1: # 탐지 실패 시
            header_index = None

    # is_header가 False인 경우, header_index는 그대로 None으로 유지됩니다.

    # 5. trimmer에게 실무 처리를 위임하고, 결과와 상세 정보를 함께 받습니다.
    df_clean, info = trimmer.trim_dataframe(
        df=df_raw, 
        trim_mode=trim,
        # is_header가 False가 아닌 모든 경우(True 또는 int)에 헤더 설정을 시도합니다.
        set_header=(is_header is not False),
        header_row=header_index
    )
    
    # 6. 받은 결과와 정보를 그대로 상위 parser.py에 반환(보고)합니다.
    return df_clean, info
