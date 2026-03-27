"""CSV file parser for PyNorma."""

import logging
from typing import Dict, Literal, Optional, Tuple, Union

import pandas as pd

from pynorma.io import trimmer
from ..utils import clean_dataframe, detect_encoding
from ..detect.header_finder import detect_header_end_row

logger = logging.getLogger("pynorma")


def parse_csv(
    filepath: str,
    trim: Union[bool, Literal["auto"], dict] = "auto",
    is_header: Union[bool, int] = True,
    delimiter: Optional[str] = None,
    encoding: str = "auto",
    verbose: bool = False,
) -> Tuple[pd.DataFrame, Dict]:
    """Parse a CSV file and return the preprocessed DataFrame with metadata.

    Parameters
    ----------
    filepath : str
        Path to the CSV file.
    trim : bool or ``"auto"`` or dict
        Trimming mode passed to the trimmer.
    is_header : bool or int
        Header detection mode.
    delimiter : str, optional
        CSV field delimiter (``None`` lets pandas auto-detect).
    encoding : str
        File encoding. ``"auto"`` triggers chardet-based detection.
    verbose : bool
        Reserved for interface consistency with the top-level parser.

    Returns
    -------
    tuple of (pd.DataFrame, dict)
        The preprocessed DataFrame and a metadata dict for verbose output.
    """
    # 1. Detect encoding
    file_encoding = detect_encoding(filepath) if encoding == "auto" else encoding

    try:
        # 2. Read file — header=None so all rows are treated as data
        df_raw = pd.read_csv(
            filepath,
            header=None,
            dtype=str,
            encoding=file_encoding,
            delimiter=delimiter,
            on_bad_lines="warn",
        )
    except Exception as e:
        logger.error("Failed to read CSV '%s' (encoding=%s): %s", filepath, file_encoding, e)
        raise

    # 3. Basic cleaning
    df_raw = clean_dataframe(df_raw)

    # 4. Determine header position based on *is_header*
    header_index: Optional[int] = None
    if isinstance(is_header, int):
        header_index = is_header
    elif is_header is True:
        header_index = detect_header_end_row(df_raw)
        if header_index == -1:
            header_index = None
    # is_header is False → header_index stays None

    # 5. Delegate trimming and header assignment to the trimmer
    df_clean, info = trimmer.trim_dataframe(
        df=df_raw,
        trim_mode=trim,
        set_header=(is_header is not False),
        header_row=header_index,
    )

    return df_clean, info
