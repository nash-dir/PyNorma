import sys
import os
import pandas as pd


# 현재 파일 기준 상위 폴더를 모듈 탐색 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# debug/debug_excelparse.py
from pynorma.io.xlsx_parser import parse_excel_with_header
from pynorma.io.csv_writer import write_csv

df, header_end = parse_excel_with_header("examples/Kor119_trimmed.xlsx", verbose=True)

# header 적용 예시
df.columns = pd.MultiIndex.from_arrays(df.iloc[0:header_end+1].values)
df = df.iloc[header_end+1:].reset_index(drop=True)

print(df.head())

write_csv(df, "examples/Kor119_trimmed.csv", encoding="cp949")