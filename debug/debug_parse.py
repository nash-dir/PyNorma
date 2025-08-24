import pandas as pd

from pynorma.io.parser import parse
from pynorma.io.writer import save_dataframe
from pynorma.detect.header_finder import detect_header_end_row

df = pd.read_csv("examples/townbusiness1.csv")

df1 = parse("examples/townbusiness1.csv", 
            is_header=True, verbose=True)

print(detect_header_end_row(df1))

save_dataframe(df1, "examples/result/townbusiness1_parse.csv", 
               encoding="utf-8", quote_all=True)