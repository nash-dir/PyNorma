# PyNorma

[![CI](https://github.com/nash-dir/PyNorma/actions/workflows/ci.yml/badge.svg)](https://github.com/nash-dir/PyNorma/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.txt)

**Turn messy, real-world spreadsheets into clean, tidy tables.**

PyNorma is a Python library for preprocessing messy tabular data (CSV / XLSX). It
finds the *actual* table(s) inside a noisy sheet — past titles, merged cells,
multi-level headers, footnotes and side-by-side layouts — cleans them, and can melt
the result into tidy long form. It's built for data scientists and analysts who are
tired of hand-cleaning unstructured exports.

> **Status: `1.0.0b1` (beta).** The public `Pipeline` API is stable enough to use,
> but internals are still moving (see [Limitations & known gaps](#limitations--known-gaps)).

---

## What it does

Table detection is formalized as a single problem: reduce a raw 2-D grid to **N tables**,
each described by five 0-indexed integers.

```
TableRegion(header, top, left, bottom, right)   # right is exclusive; header = -1 means "no header"
```

From that abstraction PyNorma builds a **structural model** of each table — resolving
multi-row header blocks, row-label (stub) columns, and trailing summary/footnote rows —
and reports it back through the public API.

```
Raw file ──▶ segment into blocks ──▶ per-block table detection ──▶ structural model ──▶ clean / long-form
             (recursive XY-cut:        (6 competing strategies      (multi-row header,
              empty-column bands +      + ground-truth-free          stub columns,
              section-title rows)       quality_score)               summary trimming)
```

### Key capabilities

- **Ensemble table detection** — 6 competing strategies detect the data region; the best
  is chosen by an internal `quality_score` (type consistency, fill uniformity, header
  confidence, boundary sharpness, coverage, size). No ground truth required at runtime.
- **Multi-table sheets** — recursive XY-cut splitting finds several tables in one sheet,
  using empty-**column** bands and repeated-header / section-title rows, not just blank
  rows. Over-splitting is gated so single tables with interior gaps stay intact.
- **Structural header handling** — resolves multi-row header blocks and reports the *leaf*
  header (the name row closest to the data), detects genuinely header-less tables
  (year/month label rows, type-consistent bodies), and preserves named-but-sparse columns.
- **Long-form conversion** — a deterministic melt driven by the detected structure
  (`Pipeline(path).run(shape="long")`), the primary path toward the project's goal of
  tidy long-form output.
- **1NF violation detection** — flags columns holding multi-valued cells (e.g.
  `"drama, crime"`) using complementary atom-overlap and consistent-list signals plus
  date-column exclusion (1.0 recall on the testbed's 5 multi-valued files).
- **Preprocessing toolkit** — importable helpers `atomize_by_column` / `atomize_by_row`
  (explode multi-valued cells), `flatten` (wide multi-header → long), `clarify`
  (dictionary value standardization), `merge` (dedupe by summing numerics), and `append`
  (header-aware vertical concat).

---

## Installation

PyNorma is not yet on PyPI. Install from source:

```bash
git clone https://github.com/nash-dir/PyNorma.git
cd PyNorma
pip install -e .            # add ".[cli]" for the CLI, ".[dev]" for tests
```

Runtime dependencies: `pandas`, `openpyxl`, `chardet` (Python ≥ 3.10).

> **Note:** the detection engine ships inside the `pynorma` package (`pynorma/detect/`), so
> installing the wheel includes it — no `specimen/` checkout is needed at runtime.
> `specimen/` and `testbed/` hold benchmark tooling and data only.

---

## Quickstart

### One call (auto-detect everything)

```python
from pynorma import Pipeline

df = Pipeline("messy_report.xlsx").run()        # detect → clean, returns a wide DataFrame
print(df.head())
```

### Tidy long form

```python
from pynorma import Pipeline

long_df = Pipeline("wide_multiheader.csv").run(shape="long")
```

### Multiple tables in one sheet

```python
p = Pipeline("multi_table_sheet.xlsx")
p.detect().clean()

for i, table in enumerate(p.all_tables()):
    print(f"Table {i}: {table.shape}")
```

### Step-by-step control

```python
from pynorma import Pipeline

df = (Pipeline("data.xlsx", strategy="D")  # pin a single strategy, or omit for auto-select
      .detect()                            # find table region(s) + build structural model
      .clean()                             # extract & clean the primary table
      .atomize(cols=["tags"], delimiter=",")   # explode multi-valued cells (1NF)
      .result())
```

### Detect multi-valued columns (1NF violations)

```python
from pynorma import detect_multivalue_columns

result = detect_multivalue_columns(df)
# e.g. [("genres", "|", 1.0)]  → the "genres" column holds pipe-separated lists
```

The full public API is `Pipeline`, `parse`, `save_dataframe`, `flatten`,
`atomize_by_column`, `atomize_by_row`, `detect_multivalue_columns`, `clarify`,
`append`, `merge` (see [`pynorma/__init__.py`](pynorma/__init__.py)).

### Command line

Install the `[cli]` extra (`pip install ".[cli]"`) to get the `pynorma` command (also
runnable as `python -m pynorma`):

```bash
pynorma detect messy.xlsx                            # list detected table(s) + shapes
pynorma clean messy.csv                              # preview the cleaned table
pynorma clean messy.csv -o tidy.csv                  # write the cleaned table
pynorma clean report.xlsx --shape long -o tidy.csv   # clean + melt to long form
pynorma clean sheet.xlsx -t 1 -o table1.csv          # pick a table on a multi-table sheet
pynorma clean book.xlsx --sheet 2 -o data.csv        # read a specific worksheet (name or index)
```

---

## Benchmarks

PyNorma ships with two evaluation harnesses. Numbers below are from a full local run on
the committed code (`pynorma 1.0.0b1`); reproduce them with the commands in
[BENCHMARK.md](BENCHMARK.md).

### Testbed — the primary metric (public `Pipeline` vs human-verified ground truth)

55 curated messy files (22 synthetic single-hazard specimens + 33 real-world), each with
a hand-verified label. A file **passes** when table-count matches **and** region IoU ≥ 0.60
**and** column-count matches.

| Metric | Value |
|---|---|
| Pass rate | **55 / 55 (100%)** |
| Mean region IoU | **0.984** |
| Mean header accuracy | **0.982** |
| Table-count match | **55 / 55** |

Pass rate holds at 100% across every difficulty tier (easy 9/9, medium 28/28, hard 11/11,
adversarial 7/7). Details and per-file results: [testbed/README.md](testbed/README.md) and
[testbed/results/scorecard.md](testbed/results/scorecard.md).

### Long-form conversion — cell-level F1 (36 hand-labeled specimens)

| Metric | Value |
|---|---|
| Micro precision / recall / F1 | **0.9997 / 1.0000 / 0.9998** |
| Macro F1 | **0.9981** |
| Perfectly-reconstructed files | **34 / 36** |

Plus **377 unit / regression tests pass** (`pytest`). See [BENCHMARK.md](BENCHMARK.md) for
the full report, methodology, and reproduction steps.

> These scores describe PyNorma on *this* corpus of known-hard cases — not a guarantee for
> arbitrary input. The limitations below are exactly where it still slips.

---

## Limitations & known gaps

Reported honestly so you know what to check on your own data:

- **1NF detection is heuristic.** Multi-valued-column recall is 1.0 on the testbed's 5 such
  files (high-cardinality lists and a mojibake header included), but detection is signal-based
  and can still over-flag or miss on unfamiliar data (e.g. it over-flags URL columns). It is
  **not** part of the testbed pass criteria.
- **One worksheet per workbook.** For multi-sheet XLSX, PyNorma auto-selects the tabular
  sheet (skipping a cover/readme sheet) or honors an explicit `sheet=` / `--sheet`; it does
  not yet combine data spread across several sheets.
- **Delimiter coverage.** Comma/tab/semicolon/pipe are detected, plus `::` and space-aligned
  columns as fallbacks; other exotic or single-space separators may still not be recognized.
- **Auto-select can favor large regions.** The ground-truth-free `quality_score` includes
  coverage/size terms that bias selection toward bigger regions; if multi-table block
  selection ever looks wrong, check there first.
- **Performance.** Large files can take tens of seconds — the largest testbed file
  (`uci_adult_census`, ~32k rows) takes ~20 s in the tracked run, as `segment_blocks`
  re-scans the full grid multiple times. Correct, but not yet optimized.

---

## Project structure

```
pynorma/
├── pynorma/                    # Installable package (public API)
│   ├── __init__.py             # Public exports
│   ├── pipeline.py             # Pipeline: detect → clean → atomize/clarify/merge → long-form
│   ├── io/                     # File I/O (CSV, XLSX), legacy trimmer
│   ├── detect/                 # Detection engine (in-package, shipped in the wheel)
│   │   ├── core.py             # TableModel, build_table_model, segment_blocks, to_long, …
│   │   ├── preprocess.py       # detect(): ensemble orchestration + fallback
│   │   ├── strategies/         # 6 competing detection strategies (A–F)
│   │   └── *_finder.py         # legacy 3-phase helpers still used by the io/ parsers
│   └── preprocessor/           # atomizer, clarifier, merger, flattener, appender modules
├── specimen/
│   └── benchmark/              # Long-form F1 benchmark tooling (not the engine)
│       ├── evaluate.py         # Long-form cell-level F1 harness (ground_truth.json)
│       └── tests/              # Structure / regression tests for the engine
├── testbed/                    # Primary benchmark
│   ├── manifest.json           # 55 human-verified ground-truth labels
│   ├── runner.py               # Scores the public Pipeline against manifest.json
│   ├── fetch.py                # Rebuilds the (gitignored) data pool
│   └── results/scorecard.md    # Latest run snapshot
├── tests/                      # Package-level unit tests
├── BENCHMARK.md                # Consolidated benchmark report
└── CHANGELOG.md
```

Benchmark **data** (`testbed/data/`, `specimen/*.csv|xlsx`) is gitignored by design — only
the labels and rebuild scripts are tracked. Regenerate with `python testbed/fetch.py` (and
the `specimen/_collect_*.py` / `_generate_*.py` scripts).

---

## Author & license

Created by [nash-dir](https://github.com/nash-dir). Released under the MIT License
(see [LICENSE.txt](LICENSE.txt)).
