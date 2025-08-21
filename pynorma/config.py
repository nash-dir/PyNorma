
import os
from typing import List

# Global variables to cache the loaded configuration
_delimiters = None
_nan_like = None

def _load_from_file(filename: str, start_marker: str = None) -> List[str]:
    """Helper function to load lines from a config file."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, filename)

    if not os.path.exists(config_path):
        print(f"[Warning] Config file not found at: {config_path}")
        return []

    with open(config_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    start_index = 0
    if start_marker:
        try:
            start_index = lines.index(start_marker + '\n') + 1
        except ValueError:
            return []

    values = [
        line.strip()
        for line in lines[start_index:]
        if line.strip() and not line.strip().startswith('#')
    ]
    return values

def get_delimiters() -> List[str]:
    """
    Loads and returns the list of delimiters from 'delimiters.txt'.
    The result is cached to avoid repeated file reads.
    """
    global _delimiters
    if _delimiters is None:
        _delimiters = _load_from_file("config/delimiters.txt", "#--- Delimiter Candidates ---")
    return _delimiters

def get_nan_like() -> List[str]:
    """
    Loads and returns the list of NaN-like values from 'nan_like.txt'.
    The result is cached to avoid repeated file reads.
    """
    global _nan_like
    if _nan_like is None:
        _nan_like = _load_from_file("config/nan_like.txt")
    return _nan_like
