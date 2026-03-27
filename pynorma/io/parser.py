"""
Unified file parser — the main user-facing entry point for PyNorma I/O.

Automatically detects file type by extension and delegates to the
appropriate sub-parser (CSV or XLSX).
"""

import logging
import os
from typing import Literal, Optional, Union

import pandas as pd

from pynorma.io import csv_parser, xlsx_parser

logger = logging.getLogger("pynorma")


def parse(
    filepath: str,
    # --- Structure detection & control ---
    trim: Union[bool, Literal["auto"], dict] = "auto",
    is_header: Union[bool, int] = True,
    # --- Format-specific options ---
    delimiter: Optional[str] = None,
    sheet_name: Union[str, int, None] = None,
    # --- Utilities ---
    encoding: str = "auto",
    verbose: bool = False,
) -> pd.DataFrame:
    """Parse a file, auto-detect its format, and apply smart preprocessing.

    This is PyNorma's primary API — the first function most users call.

    Parameters
    ----------
    filepath : str
        Path to the file to parse.
    trim : bool or ``"auto"`` or dict
        How to remove surrounding noise.

        - ``"auto"``: intelligently detect the table region (default).
        - ``False``: disable trimming.
        - ``dict``: manually specify ``{'top': …, 'bottom': …, 'left': …, 'right': …}``.
    is_header : bool or int
        Header handling.

        - ``True``: auto-detect header position (default).
        - ``False``: treat as headerless.
        - ``int``: absolute row index of the header.
    delimiter : str, optional
        *CSV only* — field delimiter.  ``None`` lets pandas guess.
    sheet_name : str or int or None
        *XLSX only* — sheet to read.  ``None`` auto-selects the
        sheet with the most data.
    encoding : str
        File encoding.  ``"auto"`` triggers automatic detection.
    verbose : bool
        If ``True``, print a summary of the parsing process.

    Returns
    -------
    pd.DataFrame
        The preprocessed DataFrame.
    """
    file_extension = os.path.splitext(filepath)[1].lower()

    # 1. Delegate to the format-specific sub-parser.
    if file_extension == ".csv":
        df, info = csv_parser.parse_csv(
            filepath,
            trim=trim,
            is_header=is_header,
            delimiter=delimiter,
            encoding=encoding,
            verbose=verbose,
        )
    elif file_extension in [".xlsx", ".xls"]:
        df, info = xlsx_parser.parse_xlsx(
            filepath,
            trim=trim,
            is_header=is_header,
            sheet_name=sheet_name,
            encoding=encoding,
            verbose=verbose,
        )
    else:
        raise ValueError(f"Unsupported file type: '{file_extension}'")

    # 2. Print verbose summary if requested.
    if verbose and info:
        original_shape = info.get("original_shape", ("N/A", "N/A"))
        trimmed_shape = info.get("trimmed_shape", ("N/A", "N/A"))

        logger.info("-" * 50)
        logger.info("[PyNorma] Parsed: %s", os.path.basename(filepath))
        logger.info("-" * 50)
        logger.info("  File Type       : %s", file_extension)
        if "detected_sheet" in info:
            logger.info("  Detected Sheet  : '%s'", info["detected_sheet"])
        logger.info(
            "  Trim Border     : top=%s, bottom=%s, left=%s, right=%s",
            info.get("top"),
            info.get("bottom"),
            info.get("left"),
            info.get("right"),
        )
        logger.info(
            "  Shape Change    : Original(%sR, %sC) -> Final(%sR, %sC)",
            original_shape[0],
            original_shape[1],
            trimmed_shape[0],
            trimmed_shape[1],
        )
        logger.info("  Header Index    : %s", info.get("header_row_abs"))
        logger.info("-" * 50)

    # 3. Return the preprocessed DataFrame.
    return df
