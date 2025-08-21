import sys
import os
import pandas as pd

# 현재 파일 기준 상위 폴더를 모듈 탐색 경로에 추가
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.normpath(os.path.join(BASE_DIR, ".."))  # 최상위 경로
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from pynorma.io.csv_parser import parse_csv
from pynorma.io.csv_writer import write_csv
from pynorma.preprocessor.flattener import flatten
from pynorma.utils import detect_header_end_row

csv_path = os.path.join(BASE_DIR, "..", "examples", "Kor119_trimmed.csv")

# df = pd.read_csv(csv_path)

df = parse_csv(csv_path, isheader=True)

headrow = detect_header_end_row(df)
print(headrow)

df_flattened = flatten(df, vertical_feature_names=['Region'], horizontal_feature_names = ['year', 'result', 'occasion'], data_feature = 'cases')

print('\nFlattened dataframe:')
print(df_flattened.head())

write_csv(df_flattened, "examples/result/Kor119_flattened.csv", filetype="csv", encoding="utf-8", quote_all=True)

print('\nSuccessfully created debug_flattener.py')
