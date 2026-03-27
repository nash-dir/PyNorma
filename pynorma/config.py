"""
Centralized configuration management for PyNorma.

Loads and caches delimiter candidates and NaN-like values from
text files in the ``config/`` directory.
"""

import logging
import os
from typing import List

logger = logging.getLogger("pynorma")

# Global variables to cache the loaded configuration
_delimiters = None
_nan_like = None


def _load_from_file(filename: str, start_marker: str = None) -> List[str]:
    """Load non-empty, non-comment lines from a config file.

    Parameters
    ----------
    filename : str
        Path relative to *this* module's directory (e.g. ``config/delimiters.txt``).
    start_marker : str, optional
        If given, only lines **after** the marker are returned.

    Returns
    -------
    List[str]
        Stripped, non-empty values.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, filename)

    if not os.path.exists(config_path):
        logger.warning("Config file not found at: %s", config_path)
        return []

    with open(config_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    start_index = 0
    if start_marker:
        try:
            start_index = lines.index(start_marker + "\n") + 1
        except ValueError:
            return []

    values = [
        line.strip()
        for line in lines[start_index:]
        if line.strip() and not line.strip().startswith("#")
    ]
    return values


def get_delimiters() -> List[str]:
    """Return the list of delimiter candidates from ``config/delimiters.txt``.

    Results are cached to avoid repeated file reads.
    """
    global _delimiters
    if _delimiters is None:
        _delimiters = _load_from_file(
            "config/delimiters.txt", "#--- Delimiter Candidates ---"
        )
    return _delimiters


def get_nan_like() -> List[str]:
    """Return the list of NaN-like values from ``config/nan_like.txt``.

    Results are cached to avoid repeated file reads.
    """
    global _nan_like
    if _nan_like is None:
        _nan_like = _load_from_file("config/nan_like.txt")
    return _nan_like
