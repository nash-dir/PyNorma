from pathlib import Path

current_file_path = Path(__file__)
parent_dir = current_file_path.parent

from pynorma.io.parser import parse
from pynorma.preprocessor.appender import append
from pynorma.io.writer import save_dataframe


df1 = parse("examples/townbusiness1.csv", is_header=True, verbose=True)
df2 = parse("examples/townbusiness2.csv", is_header=False, verbose=True)
dfa = append(df1, df2)

df3 = parse("examples/townbusiness3.csv", is_header=True, verbose=True)
dfb = append(dfa, df3)

save_dataframe(dfb, "examples/result/townbusiness_append.csv", encoding="utf-8", quote_all=True)
