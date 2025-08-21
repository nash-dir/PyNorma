# PyNorma

**"You gotta do it, you can do it, but you just don't wanna do it."**

PyNorma is a Python library that provides insights and automation for preprocessing messy, real-world tabular data. It's designed for data scientists, analysts, and anyone who's tired of the tedious task of cleaning up unstructured spreadsheets.

## Key Features

- **Smart Table Detection**: Automatically finds the main data table within messy Excel or CSV files, ignoring surrounding comments and empty spaces.
- **Advanced Preprocessing**: Includes powerful tools like:
    - `Flattener`: Converts wide, multi-level header tables into a tidy, long format.
    - `Atomizer`: Splits cells with multiple values into distinct rows or columns.
    - `Clarifier`: Standardizes data based on a custom dictionary.
    - ...and more.
- **Developer-Friendly**: Designed by a lazy developer for lazy (but smart) developers.

## Installation

```bash
pip install pynorma
```


## Quickstart
Here's a simple example of reading a messy Excel file and automatically trimming it to the core data table.

```python
from pynorma.io import parser
from pynorma.preprocessor import trimmer

# 1. Parse the file - PyNorma automatically detects the file type.
raw_df = parser.parse("examples/townbusiness1.csv")

# 2. Automatically trim the dataframe to the main table area.
clean_df = trimmer.trim_dataframe(raw_df, trim_mode="auto")

print("Successfully cleaned the dataframe!")
print(clean_df.head())
```

## Author
nash-dir (https://github.com/nash-dir)

## License
This project is licensed under the MIT License.

