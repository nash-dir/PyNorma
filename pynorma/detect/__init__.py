"""Detection utilities for finding tables and headers in messy data."""

from pynorma.detect.header_finder import detect_header_end_row
from pynorma.detect.table_finder import find_robust_table_area

__all__ = ["detect_header_end_row", "find_robust_table_area"]
