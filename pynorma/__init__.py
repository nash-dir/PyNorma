"""
PyNorma — A smart tool for preprocessing messy tabular data.

Provides insights and automation for cleaning up unstructured
spreadsheets, Excel files, and CSV data.
"""

from pynorma.io.parser import parse
from pynorma.io.writer import save_dataframe
from pynorma.preprocessor.flattener import flatten
from pynorma.preprocessor.atomizer import atomize_by_column, atomize_by_row, detect_multivalue_columns
from pynorma.preprocessor.clarifier import clarify
from pynorma.preprocessor.appender import append
from pynorma.preprocessor.merger import merge
from pynorma.pipeline import Pipeline

__version__ = "1.0.0a1"
__all__ = [
    "parse",
    "save_dataframe",
    "flatten",
    "atomize_by_column",
    "atomize_by_row",
    "detect_multivalue_columns",
    "clarify",
    "append",
    "merge",
    "Pipeline",
]

