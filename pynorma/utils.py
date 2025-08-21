import pandas as pd
import chardet
from typing import List, Tuple, Optional, Dict
from . import config


## Input / Output
def detect_encoding(file_path: str) -> str:
    """Detects the encoding of a file.

    Parameters
    ----------
    file_path : str
        The path to the file.

    Returns
    -------
    str
        The detected encoding.
    """
    with open(file_path, 'rb') as f:
        raw_data = f.read()
    result = chardet.detect(raw_data)
    return result['encoding']


def replace_nan_like(
    df: pd.DataFrame,
    custom_na_values: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Converts NaN-like values to pandas NA.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to clean.
    custom_na_values : Optional[List[str]], optional
        A list of custom NaN-like values, by default None

    Returns
    -------
    pd.DataFrame
        The cleaned DataFrame.
    """
    df_cleaned = df.copy()

    # Load NaN-like terms from config and user input
    na_values_from_dict = config.get_nan_like()
    na_values_from_list = custom_na_values if custom_na_values else []
    all_na_values = list(set(na_values_from_dict + na_values_from_list))

    if all_na_values:
        df_cleaned.replace(all_na_values, pd.NA, inplace=True)

    return df_cleaned


def clean_dataframe(
    df: pd.DataFrame,
    custom_na_values: Optional[List[str]] = None
) -> pd.DataFrame:
    """Cleans a DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to clean.
    custom_na_values : Optional[List[str]], optional
        A list of custom NaN-like values, by default None

    Returns
    -------
    pd.DataFrame
        The cleaned DataFrame.
    """
    cleaned = df.applymap(lambda x: pd.NA if isinstance(x, str) and x.strip() == "" else x)
    cleaned = replace_nan_like(cleaned, custom_na_values)
    return cleaned


def find_largest_soft_rectangle(
    df,
    row_offset: int = 0,
    col_offset: int = 0,
    tolerance: float = 0.1,
    min_score: float = 0.8
):
    """
    Finds the largest rectangle within a DataFrame or binary mask,
    allowing some non-numeric cells using fuzzy logic and NaN-like values.

    Parameters:
        df (Union[pd.DataFrame, np.ndarray]): Input DataFrame or binary mask.
        row_offset (int): Number of rows to skip from the top.
        col_offset (int): Number of columns to skip from the left.
        tolerance (float): Allowed proportion of 0s in a candidate region.
        min_score (float): Minimum numeric density to qualify as valid rectangle.

    Returns:
        Tuple[int, int, int, int]: (top, bottom, left, right) indices of the best rectangle.
    """
    import numpy as np

    na_like_set = set(config.get_nan_like())

    def is_numeric_or_nanlike(x):
        if pd.isna(x):
            return True
        if isinstance(x, str) and x.strip() in na_like_set:
            return True
        try:
            float(x)
            return True
        except (ValueError, TypeError):
            return False

    # Determine binary mask depending on input type
    if isinstance(df, pd.DataFrame):
        binary_mask = df.applymap(is_numeric_or_nanlike).astype(int).values
    elif isinstance(df, np.ndarray):
        binary_mask = df  # assume already binary mask
    else:
        raise TypeError("Input must be a pandas DataFrame or numpy ndarray")

    rows, cols = binary_mask.shape
    max_area = 0
    best_rect = (0, 0, 0, 0)
    heights = [0] * cols

    for i in range(row_offset, rows):
        for j in range(col_offset, cols):
            if binary_mask[i][j]:
                heights[j] += 1
            else:
                heights[j] = 0

        stack = []
        for j in range(cols + 1):
            curr_height = heights[j] if j < cols else 0
            while stack and curr_height < heights[stack[-1]]:
                h = heights[stack.pop()]
                w = j if not stack else j - stack[-1] - 1
                left = stack[-1] + 1 if stack else 0
                top = i - h + 1
                bottom = i + 1
                right = j

                region = binary_mask[top:bottom, left:right]
                total = h * w
                zeros = (region == 0).sum()
                score = (total - zeros) / total if total > 0 else 0

                if zeros <= total * tolerance and score >= min_score:
                    if total > max_area:
                        max_area = total
                        best_rect = (top, bottom, left, right)

            stack.append(j)

    return best_rect
