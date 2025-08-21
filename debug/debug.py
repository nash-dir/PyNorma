from pynorma.io.CSV_parser import parse
from pynorma.io.CSV_writer import write_output
from pynorma.preprocessor.atomizer import atomize

df_trimmed = parse("examples/townbusiness1.csv", verbose=True)
print('parsed & trimmed dataframe:')
print(df_trimmed.head())

df_atomized = atomize(df_trimmed)
print('atomized dataframe:')
print(df_atomized.head())
write_output(df_atomized, "examples/result/townbusiness1_ta.csv", filetype="csv", encoding="utf-8", quote_all=True)

from pynorma.preprocessor.merger import merge
df_merged = merge(df_atomized, ['count', 'staff'])
print('merged dataframe:')
print(df_merged.head())
write_output(df_merged, "examples/result/townbusiness1_tam.csv", filetype="csv", encoding="utf-8", quote_all=True)

from pynorma.preprocessor.clarifier import clarify
df_clarified = clarify(df_merged, column="Business", dict_path="examples/townbusiness_dict.csv", sum_columns=["count", "staff"])
print('clarified dataframe:')
print(df_clarified.head())
write_output(df_clarified, "examples/result/townbusiness1_clarified.csv", filetype="csv", encoding="utf-8", quote_all=True)

