from pynorma.io.xlsx_parser import parse_excel
import pandas as pd

df_excel = parse_excel('examples/crimetable.xlsx')
df_csv = pd.read_csv('examples/result/crimetable_parsed.csv')

print(f"Excel columns: {len(df_excel.columns)}")
print(f"CSV columns: {len(df_csv.columns)}")

# 각 열의 이름을 비교 (앞 5개만)
print("\n--- Column Name Comparison (First 5) ---")
for i in range(min(5, len(df_excel.columns), len(df_csv.columns))):
    print(f"Excel Col {i}: {df_excel.columns[i]}")
    print(f"CSV Col {i}:   {df_csv.columns[i]}")
    print("-" * 20)
