# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- **Structural table detection** (`pynorma/detect/core.py`): `TableModel` +
  `build_table_model` resolve multi-row header blocks (reporting the *leaf* header row),
  row-label/stub columns, and trailing summary/footnote trimming.
- **Recursive XY-cut multi-table segmentation** (`segment_blocks`): splits side-by-side and
  stacked tables using empty-**column** bands and section-title / repeated-header rows, with
  over-split gates so single tables with interior gaps stay intact.
- **Header-less table detection** (`_has_header`): label-over-data + year/month label +
  body type-consistency signals.
- `Pipeline.run(shape="long")` / `Pipeline.to_long()`: deterministic long-form melt driven
  by the detected structure.
- **Testbed benchmark** (`testbed/`): 55 human-verified files, `runner.py` scoring the public
  `Pipeline` against `manifest.json`, `CATALOG.md`, and a committed `results/scorecard.md`.
- `BENCHMARK.md`: consolidated, reproducible benchmark report.
- **Command-line interface** (`pynorma` console script + `python -m pynorma`):
  `pynorma clean <file> [-o out] [--shape long] [--strategy A-F] [-t N]` and
  `pynorma detect <file>` (requires the `[cli]` extra).
- `py.typed` marker — PyNorma now ships PEP 561 inline type information.
- `pyproject.toml` with PEP 621 metadata, replacing `setup.py`
- Public API via `pynorma/__init__.py` (`parse`, `save_dataframe`, `flatten`, `atomize_by_column`, `atomize_by_row`, `clarify`, `append`, `merge`)
- `__version__` attribute
- `detect/__init__.py` package initializer
- `preprocessor/__init__.py` with re-exports
- Comprehensive pytest test suite (`tests/test_parser.py`, `tests/test_detect.py`, `tests/test_preprocessor.py`)
- GitHub Actions CI workflow (`.github/workflows/ci.yml`)
- This `CHANGELOG.md`

### Fixed
- **1NF detection robustness** (`detect_multivalue_columns`): iterate columns positionally
  (fixes a crash on duplicate column labels — e.g. the IMDb file's two `Director` columns);
  exclude date-like columns (no longer mis-flags `date_added`); add a consistent-list signal
  for high-cardinality lists whose atoms rarely repeat (e.g. a `cast`). Testbed 1NF recall
  **0.733 → 1.0** across the 5 multi-valued files (netflix 0.667→1.0, imdb 0.0→1.0).
- `detect_multivalue_columns` docstring example now reports the actual overlap ratio
  (`0.667`, was `0.857`)

### Changed
- **Detection engine promoted into the package (Step 0).** Moved `core`, `preprocess`, and
  `strategies/` from `specimen/benchmark/` into the installable `pynorma/detect/`, and removed
  the `sys.path` shim in `pipeline.py` / `io/trimmer.py`. `pip install pynorma` now ships the
  full detection engine — no `specimen/` checkout needed at runtime. `specimen/` retains only
  the long-form F1 harness (`evaluate.py`), the engine tests, and ground truth. Testbed 55/55,
  long-form micro-F1 0.9998, and 377 unit tests all unchanged.
- CI now also runs the engine tests (`specimen/benchmark/tests`, which skip gracefully when
  the gitignored corpus is absent) and smoke-tests the CLI; installs the `[cli]` extra.
- `requirements.txt` trimmed to the core runtime deps; CLI/dev deps live in the `[cli]` /
  `[dev]` extras, matching `pyproject.toml`.
- **BREAKING**: `xlsx_parser.parse_xlsx()` now returns `Tuple[DataFrame, Dict]` (was `DataFrame`)
- **BREAKING**: `xlsx_parser.parse_xlsx()` parameter `sheet` renamed to `sheet_name`
- **BREAKING**: `xlsx_parser.parse_xlsx()` parameter `set_header` renamed to `is_header`
- Replaced all `print()` statements with `logging` module across all modules
- Replaced deprecated `DataFrame.applymap()` with `DataFrame.map()` (`utils.py`)
- Moved `numpy` import from function-level to module-level (`utils.py`)
- Extracted magic numbers in `header_finder.py` into keyword parameters (`numeric_row_threshold`, `string_row_threshold`, `min_diff_count`)
- Extracted hardcoded score threshold in `atomizer.detect_feature_delimiter()` into `min_score` parameter
- Translated all Korean comments and docstrings to English across the entire codebase
- Translated Korean error message in `writer.py` to English
- Cleaned up verbose debug comments in `table_finder.py`
- Minimum Python version bumped from 3.8 to 3.10

### Removed
- `setup.py` (replaced by `pyproject.toml`)
- Dead code in `flattener.py` (`left += 0`, `right += 0`)

## [1.0.0a1] — 2026-03-15

### Added
- Initial alpha release
- Smart table detection (`detect/header_finder.py`, `detect/table_finder.py`)
- File parsers (`io/parser.py`, `io/csv_parser.py`, `io/xlsx_parser.py`)
- Smart trimmer (`io/trimmer.py`)
- File writer (`io/writer.py`)
- Preprocessors: Flattener, Atomizer, Clarifier, Appender, Merger
- Configuration system (`config.py`, `config/delimiters.txt`, `config/nan_like.txt`)
- Utility functions (`utils.py`)
