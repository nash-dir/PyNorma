"""DataFrame writer — save to CSV, TSV, or XLSX with auto-format detection."""

import csv
import logging
import os
from typing import Optional

import pandas as pd

logger = logging.getLogger("pynorma")


def save_dataframe(
    df: pd.DataFrame,
    output_path: str,
    encoding: str = "utf-8-sig",
    quote_all: bool = False,
) -> None:
    """Save a DataFrame to a file, auto-detecting the format from the extension.

    Supported formats: ``.csv``, ``.tsv``, ``.xlsx``.
    Missing directories in *output_path* are created automatically.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to save.
    output_path : str
        Destination file path (e.g. ``'data/result.csv'``).
    encoding : str
        Encoding for CSV/TSV files.  Defaults to ``'utf-8-sig'`` so that
        Korean text opens correctly in Excel.
    quote_all : bool
        If ``True``, wrap every field in quotes.
    """
    # Auto-create parent directories
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    file_extension = os.path.splitext(output_path)[1].lower()
    quoting = csv.QUOTE_ALL if quote_all else csv.QUOTE_MINIMAL

    if file_extension == ".csv":
        df.to_csv(output_path, index=False, encoding=encoding, quoting=quoting)
    elif file_extension == ".tsv":
        df.to_csv(output_path, index=False, sep="\t", encoding=encoding, quoting=quoting)
    elif file_extension == ".xlsx":
        df.to_excel(output_path, index=False)
    else:
        raise ValueError(f"Unsupported file format: '{file_extension}'")

    logger.info("DataFrame saved to %s", output_path)