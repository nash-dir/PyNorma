# PyNorma

**"You gotta do it, you can do it, but you just don't wanna do it."**

PyNorma is a Python library that provides insights and automation for preprocessing messy, real-world tabular data. It's designed for data scientists, analysts, and anyone who's tired of the tedious task of cleaning up unstructured spreadsheets.

## Key Features

- **Ensemble Table Detection**: 6 competing strategies auto-detect the data region within messy files, scored and selected by an internal quality metric — no ground truth required.
- **Pipeline API**: A fluent, chainable interface connects detection → cleaning → transformation in one call.
- **Preprocessing Toolkit**:
    - `Atomizer`: Splits cells with multiple values into distinct rows or columns (1NF normalization).
    - `Flattener`: Converts wide, multi-level header tables into a tidy, long format.
    - `Clarifier`: Standardizes data values using a custom dictionary mapping.
    - `Merger`: Deduplicates rows by summing numeric columns.
    - `Appender`: Vertically concatenates DataFrames with smart header alignment.

## Installation

```bash
pip install pynorma
```

## Quickstart

### One-liner (auto-detect everything)

```python
from pynorma import Pipeline

df = Pipeline("messy_report.xlsx").run()
print(df.head())
```

### Full control

```python
from pynorma import Pipeline

df = (Pipeline("data.xlsx", strategy="D")
      .detect()                                    # Find table regions
      .clean()                                     # Extract & clean
      .atomize(cols=["Tags"], delimiter=",")        # Explode multi-valued cells
      .clarify("업종", "dict.csv", sum_columns=["매출"])  # Standardize values
      .merge(sum_columns=["매출"])                  # Deduplicate
      .result())
```

### Legacy API

```python
import pynorma

df = pynorma.parse("data.csv", trim="auto")
```

## Architecture

```
Raw File ──→ Detection ──→ Cleaning ──→ DataFrame ──→ Preprocessor ──→ Clean Output
             6 strategies    common       pandas       atomize
             quality_score   pipeline                  clarify
             auto-select                               merge / flatten
```

### Detection: Table as N × 5 Integers

PyNorma reduces the table detection problem to finding **N tables**, each described by 5 integers:

```
(header, top, left, bottom, right)
```

Six strategies compete on each file, and the best is selected via a ground-truth-free `quality_score` based on type consistency, fill uniformity, header confidence, and boundary sharpness.

| Strategy | Approach | Avg Score |
|----------|----------|-----------|
| D_Pattern | Regex normalization + type ratio | 0.991 |
| C_Gradient | Density gradient boundary detection | 0.989 |
| B_Entropy | Entropy jump detection | 0.967 |
| F_Voting | Column-type voting | 0.964 |
| A_Rules | Fixed heuristic rules | 0.960 |
| E_Window | Sliding window density | 0.916 |

Benchmarked on **36 specimens** (24 real-world + 12 adversarial edge cases) with **60 regression tests**.

## Project Structure

```
pynorma/
├── pynorma/                    # Main package
│   ├── pipeline.py             # Pipeline API (detection → preprocessor)
│   ├── io/                     # File I/O (CSV, XLSX)
│   ├── detect/                 # Table region detection (legacy)
│   └── preprocessor/           # Atomizer, Clarifier, Merger, Flattener, Appender
├── specimen/                   # Test data (36 files)
│   └── benchmark/              # Ensemble detection framework
│       ├── core.py             # TableRegion, quality_score, clean_region
│       ├── preprocess.py       # detect() + preprocess() public API
│       ├── strategies/         # 6 competing detection strategies
│       └── tests/              # 60 regression tests
└── tests/                      # Package-level tests
```

## Author

nash-dir (https://github.com/nash-dir)

## License

This project is licensed under the MIT License.
