# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `pyproject.toml` with PEP 621 metadata, replacing `setup.py`
- Public API via `pynorma/__init__.py` (`parse`, `save_dataframe`, `flatten`, `atomize_by_column`, `atomize_by_row`, `clarify`, `append`, `merge`)
- `__version__` attribute
- `detect/__init__.py` package initializer
- `preprocessor/__init__.py` with re-exports
- Comprehensive pytest test suite (`tests/test_parser.py`, `tests/test_detect.py`, `tests/test_preprocessor.py`)
- GitHub Actions CI workflow (`.github/workflows/ci.yml`)
- This `CHANGELOG.md`

### Changed
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
