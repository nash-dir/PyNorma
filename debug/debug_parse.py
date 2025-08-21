import pandas as pd
from pynorma.io.CSV_parser import parse

df_trimmed = parse("examples/townbusiness2.csv", isheader=False, verbose=True)

