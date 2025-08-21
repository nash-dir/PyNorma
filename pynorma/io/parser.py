import os
from . import csv_parser, xlsx_parser


def parse(filepath: str, **kwargs):
    """Parses a file,
    automatically detecting the filetype,
    and calling the appropriate parser.

    Parameters
    ----------
    filepath : str
        The path to the file to parse.
    **kwargs
        Keyword arguments to pass to the parser.

    Returns
    -------
    pd.DataFrame
        The parsed DataFrame.
    """
    file_extension = os.path.splitext(filepath)[1].lower()

    if file_extension == '.csv':
        return csv_parser.parse_csv(filepath, **kwargs)
    elif file_extension == '.xlsx':
        return xlsx_parser.parse_xlsx(filepath, **kwargs)
    else:
        raise ValueError(f"Unsupported filetype: {file_extension}")
