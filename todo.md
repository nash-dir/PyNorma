# pynorma To-Do List

This document outlines planned improvements and refactoring tasks for the `pynorma` library.

## 1. Project-Wide Refinements

### 1.1. Centralize Configuration Management
- **Task:** Create a single configuration module (e.g., `pynorma/config.py`).
- **Details:** This module should handle loading `delimiters.txt` and `nan_like.txt`. Functions like `atomizer.load_candidates` and `utils.load_nan_dictionary` should be replaced by a unified interface from this new module. This avoids redundant file I/O and consolidates configuration logic.

### 1.2. Standardize Logging
- **Task:** Replace all `print()` statements used for status messages or errors with a proper logging framework (e.g., Python's `logging` module).
- **Affected Files:** `io/csv_parser.py`, `io/writer.py`, `preprocessor/appender.py`, etc.
- **Benefit:** Allows users of the library to control log verbosity and redirect output as needed.

### 1.3. Improve Public API
- **Task:** Use `pynorma/__init__.py` to expose a clean, user-facing API.
- **Details:** Explicitly import the most important functions (e.g., `parse`, `save_dataframe`, `clarify`, `flatten`) into the `__init__.py` file so users can do `from pynorma import parse` instead of `from pynorma.io.parser import parse`.

### 1.4. Performance Enhancements
- **Task:** Identify and refactor performance-critical sections of the code.
- **Details:** Replace loops like `iterrows` in `preprocessor/clarifier.py` and `preprocessor/atomizer.py` with vectorized pandas operations where possible. The `utils.clean_dataframe` function's use of `applymap` should also be reviewed for a faster alternative.

## 2. Module-Specific Improvements

### `detect`
- **`header_finder.py`**:
    - Make scoring weights (`'stability': 0.5`, etc.) configurable parameters instead of hardcoded values.
    - Add comments to explain the rationale behind the scoring mechanism.
- **`table_finder.py`**:
    - Make threshold ratios (`row_threshold_ratio`, `col_threshold_ratio`) configurable.

### `io`
- **`xlsx_parser.py`**:
    - The `_unmerge_cells` function modifies the worksheet in place. While it works, consider creating a new worksheet or returning a new data structure to follow functional programming principles and avoid side effects.
- **`trimmer.py`**:
    - The logic for `trim_mode` is complex. Simplify the conditional branching if possible.

### `preprocessor`
- **`appender.py`**:
    - The `isthere_header` function's logic is too simple and may lead to incorrect header detection. It should be replaced by the more robust `detect_header_end_row` from the `detect` module.
- **`atomizer.py`**:
    - The hardcoded score threshold (`0.1`) in `detect_feature_delimiter` should be a parameter.
    - Refactor `atomize_by_row` to avoid `iterrows`.
- **`flattener.py`**:
    - This module is highly complex and could benefit from being broken down into smaller, more manageable functions.
    - The use of `__SEP__` as a temporary delimiter is fragile. Explore more robust methods for joining and splitting header text.
    - The `detect_header_end_col` function's reliance on `find_largest_soft_rectangle` makes it complex. Add more detailed comments explaining the process.

### `utils.py`
- **`find_largest_soft_rectangle`**:
    - This function is very complex. Add extensive comments to explain the algorithm (e.g., the histogram-based approach for finding the largest rectangle).
    - The `import numpy as np` should be moved to the top of the file.

## 3. Documentation & Style

### 3.1. Translate Comments
- **Task:** Translate all Korean comments and docstrings to English to make the codebase accessible to a wider audience.
- **Affected Files:** `detect/header_finder.py`, `io/csv_parser.py`, `io/xlsx_parser.py`, etc.

### 3.2. Standardize Docstrings
- **Task:** Ensure all functions have clear, consistent docstrings that follow a standard format (e.g., Google Style or NumPy style).
- **Details:** Clearly document parameters, return values, and any exceptions raised.

## 4. Testing

### 4.1. Introduce a Testing Framework
- **Task:** Add a testing framework like `pytest` to the project.
- **Details:** Create a `tests/` directory and add a `requirements-dev.txt` for testing dependencies.

### 4.2. Write Unit Tests
- **Task:** Create a comprehensive test suite with high code coverage.
- **Priority Areas:**
    - `detect` module: Test header and table detection with various edge cases (e.g., no header, multiple headers, sparse tables).
    - `preprocessor` modules: Test each preprocessor function (`flatten`, `clarify`, `atomize`) with sample data.
    - `io` modules: Test parsing of malformed CSV/XLSX files.
