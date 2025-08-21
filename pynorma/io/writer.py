import pandas as pd
import csv
import os
from typing import Optional

def save_dataframe(
    df: pd.DataFrame,
    output_path: str,
    encoding: str = "utf-8-sig",
    quote_all: bool = False,
) -> None:
    """
    (개선된 방식) 데이터프레임을 파일 경로에 기반하여 자동으로 저장합니다.
    경로에 폴더가 없으면 자동으로 생성합니다.

    Args:
        df (pd.DataFrame): 저장할 데이터프레임.
        output_path (str): 저장할 파일의 전체 경로 (e.g., 'data/result.csv').
        encoding (str, optional): CSV/TSV 파일 인코딩. 엑셀에서 한글 깨짐 방지를 위해 'utf-8-sig'를 기본값으로 변경.
        quote_all (bool, optional): 모든 필드를 따옴표로 감쌀지 여부.
    """
    # 1. (개선) 폴더 자동 생성
    #    파일을 저장할 디렉토리를 확인하고, 없으면 생성합니다.
    output_dir = os.path.dirname(output_path)
    if output_dir: # output_path가 폴더 경로를 포함하는 경우
        os.makedirs(output_dir, exist_ok=True)

    # 2. (개선) 파일 타입 자동 감지
    #    파일 경로에서 확장자를 추출하여 파일 타입을 결정합니다.
    file_extension = os.path.splitext(output_path)[1].lower()

    # 3. 파일 타입에 따라 저장
    quoting = csv.QUOTE_ALL if quote_all else csv.QUOTE_MINIMAL

    if file_extension == ".csv":
        df.to_csv(output_path,
                  index=False,
                  encoding=encoding,
                  quoting=quoting)
    elif file_extension == ".tsv":
        df.to_csv(output_path,
                  index=False,
                  sep="\t",
                  encoding=encoding,
                  quoting=quoting)
    elif file_extension == ".xlsx":
        df.to_excel(output_path, index=False)
    else:
        raise ValueError(f"지원하지 않는 파일 형식입니다: '{file_extension}'")
    
    print(f"✅ DataFrame successfully saved to {output_path}")