from pynorma.io.CSV_parser import parse
from pynorma.io.CSV_writer import write_output

df1 = parse("examples/townbusiness1.csv", verbose=True)
df2 = parse("examples/townbusiness2.csv", verbose=True)

'''
from pynorma.appender import append
df3 = append(df1, df2)

print(df3.head())
write_output(df3, "examples/result/townbusiness_appended.csv", filetype="csv", encoding="utf-8", quote_all=True)
'''