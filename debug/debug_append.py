from pynorma.io.csv_parser import parse_csv
from pynorma.preprocessor.appender import append
from pynorma.io.writer import write_output


df1 = parse_csv("examples/townbusiness1.csv", isheader=True, verbose=True)
df2 = parse_csv("examples/townbusiness2.csv", isheader=False, verbose=True)
dfa = append(df1, df2, verbose=True)

df3 = parse_csv("examples/townbusiness3.csv", isheader=True, verbose=True)
dfb = append(dfa, df3, verbose=True)

write_output(dfb, "examples/result/townbusiness_append.csv", filetype="csv", encoding="utf-8", quote_all=True)

