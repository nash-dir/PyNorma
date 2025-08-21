import pandas as pd
from typing import Union, Optional, Literal, Dict

# 이제 파서는 Trimmer와 Utils의 기능을 가져다 쓰기만 하면 됩니다.
from pynorma.preprocessor import trimmer
from pynorma.utils import clean_dataframe, detect_encoding

def parse_csv(
    filepath: str,
    encoding: Union[str, Literal["auto"]] = "auto",
    trim: Union[bool, Literal["auto"], dict] = "auto",
    set_header: bool = True
) -> pd.DataFrame:
    """
    (개선된 방식) CSV 파일을 한 번만 읽고, Trimmer에게 후처리를 위임합니다.

    Args:
        filepath (str): CSV 파일 경로.
        encoding (str or "auto", optional): 파일 인코딩. "auto"일 경우 자동으로 탐지합니다.
        trim (bool, "auto", or dict, optional): 트림 모드. Trimmer에게 그대로 전달됩니다.
        set_header (bool, optional): 헤더 설정 여부. Trimmer에게 그대로 전달됩니다.

    Returns:
        pd.DataFrame: 전처리가 완료된 데이터프레임.
    """
    # 1. 인코딩을 자동으로 탐지합니다.
    file_encoding = detect_encoding(filepath) if encoding == "auto" else encoding
    
    try:
        # 2. 파일을 한 번만 읽어 raw 데이터프레임을 만듭니다.
        #    header=None으로 읽어야 모든 내용을 그대로 가져올 수 있습니다.
        df_raw = pd.read_csv(
            filepath,
            header=None,
            dtype=str,
            encoding=file_encoding,
            on_bad_lines='warn' # 혹시 모를 오류 라인에 대한 처리
        )
    except Exception as e:
        print(f"Error reading CSV file with encoding '{file_encoding}': {e}")
        # 다른 인코딩으로 재시도하거나, 더 구체적인 에러 핸들링을 추가할 수 있습니다.
        raise

    # 3. 기본적인 클리닝을 수행합니다. (e.g., 추가적인 NaN 값 처리)
    df_raw = clean_dataframe(df_raw)

    # 4. 똑똑한 Trimmer에게 트림과 헤더 설정을 모두 위임합니다.
    df_clean = trimmer.trim_dataframe(df_raw, trim_mode=trim, set_header=set_header)
    
    return df_clean