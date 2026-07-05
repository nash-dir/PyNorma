"""Tests for pynorma.preprocessor (atomizer, appender, clarifier, merger, flattener)."""

import os
import tempfile

import numpy as np
import pandas as pd
import pytest

from pynorma.preprocessor.atomizer import (
    atomize_by_column,
    atomize_by_row,
    detect_feature_delimiter,
)
from pynorma.preprocessor.appender import append, isthere_header, compare_structure
from pynorma.preprocessor.merger import merge
from pynorma.preprocessor.flattener import flatten, detect_header_end_col
from pynorma.preprocessor.clarifier import (
    load_clarify_dictionary,
    apply_clarify_mapping,
    clarify,
)


# ═══════════════════════════════════════════════════════════════════
#  detect_feature_delimiter
# ═══════════════════════════════════════════════════════════════════

class TestDetectFeatureDelimiter:
    """Tests for the in-cell delimiter detector."""

    def test_comma_delimiter(self, multi_value_df):
        assert detect_feature_delimiter(multi_value_df["Hobbies"]) == ","

    def test_semicolon_delimiter(self, multi_value_semicolon_df):
        assert detect_feature_delimiter(multi_value_semicolon_df["Tags"]) == ";"

    def test_pipe_delimiter(self, multi_value_pipe_df):
        assert detect_feature_delimiter(multi_value_pipe_df["Products"]) == "|"

    def test_no_delimiter(self, clean_df):
        assert detect_feature_delimiter(clean_df["Name"]) is None

    def test_no_delimiter_numeric_column(self):
        series = pd.Series([1, 2, 3, 4, 5])
        assert detect_feature_delimiter(series) is None

    def test_custom_candidates(self):
        series = pd.Series(["a#b", "c#d", "e#f"])
        result = detect_feature_delimiter(series, candidates=["#"])
        assert result == "#"

    def test_custom_candidates_no_match(self):
        series = pd.Series(["a,b", "c,d"])
        result = detect_feature_delimiter(series, candidates=["#", "@"])
        assert result is None

    def test_min_score_high_rejects(self, multi_value_df):
        """With min_score=0.99 and only 2/3 multi-valued, comma still passes."""
        result = detect_feature_delimiter(multi_value_df["Hobbies"], min_score=0.99)
        # 2/3 = 0.67 < 0.99, so should be None
        assert result is None

    def test_min_score_low_accepts(self):
        """Even a single multi-valued cell should pass with low threshold."""
        series = pd.Series(["a,b", "single", "single", "single"])
        result = detect_feature_delimiter(series, min_score=0.01)
        assert result == ","

    def test_all_nan_series(self):
        series = pd.Series([pd.NA, None, np.nan])
        result = detect_feature_delimiter(series)
        assert result is None

    def test_single_value_series(self):
        series = pd.Series(["a,b"])
        result = detect_feature_delimiter(series)
        assert result == ","

    def test_empty_strings(self):
        series = pd.Series(["", "", ""])
        result = detect_feature_delimiter(series)
        assert result is None


# ═══════════════════════════════════════════════════════════════════
#  atomize_by_column
# ═══════════════════════════════════════════════════════════════════

class TestAtomizeByColumn:
    """Tests for column-wise atomization (exploding rows)."""

    def test_explicit_column_and_delimiter(self, multi_value_df):
        result = atomize_by_column(multi_value_df, atm_cols=["Hobbies"], delimiter=",")
        assert len(result) == 6  # 2 + 3 + 1

    def test_auto_detect(self, multi_value_df):
        result = atomize_by_column(multi_value_df)
        assert len(result) >= len(multi_value_df)

    def test_preserves_other_columns(self, multi_value_df):
        result = atomize_by_column(multi_value_df, atm_cols=["Hobbies"], delimiter=",")
        assert "Name" in result.columns
        assert "Score" in result.columns

    def test_preserves_values_in_other_columns(self, multi_value_df):
        result = atomize_by_column(multi_value_df, atm_cols=["Hobbies"], delimiter=",")
        alice_hobbies = result[result["Name"] == "Alice"]["Hobbies"].tolist()
        assert "reading" in alice_hobbies
        assert "swimming" in alice_hobbies

    def test_single_value_cells_unchanged(self, multi_value_df):
        result = atomize_by_column(multi_value_df, atm_cols=["Hobbies"], delimiter=",")
        carol_rows = result[result["Name"] == "Carol"]
        assert len(carol_rows) == 1
        assert carol_rows.iloc[0]["Hobbies"] == "drawing"

    def test_no_matching_columns(self, clean_df):
        """If no column has delimiters, output should equal input."""
        result = atomize_by_column(clean_df)
        assert len(result) == len(clean_df)

    def test_multiple_columns(self):
        df = pd.DataFrame({
            "A": ["a,b", "c"],
            "B": ["x,y", "z"],
        })
        result = atomize_by_column(df, atm_cols=["A", "B"], delimiter=",")
        assert len(result) >= 2

    def test_whitespace_trimmed(self):
        df = pd.DataFrame({"vals": ["a , b , c"]})
        result = atomize_by_column(df, atm_cols=["vals"], delimiter=",")
        values = result["vals"].tolist()
        assert "a" in values
        assert "b" in values
        assert "c" in values

    def test_empty_parts_removed(self):
        df = pd.DataFrame({"vals": ["a,,b,"]})
        result = atomize_by_column(df, atm_cols=["vals"], delimiter=",")
        assert "" not in result["vals"].tolist()

    def test_semicolon_delimiter(self, multi_value_semicolon_df):
        result = atomize_by_column(
            multi_value_semicolon_df, atm_cols=["Tags"], delimiter=";"
        )
        assert len(result) == 6  # 2 + 3 + 1

    def test_does_not_modify_original(self, multi_value_df):
        original_len = len(multi_value_df)
        _ = atomize_by_column(multi_value_df, atm_cols=["Hobbies"], delimiter=",")
        assert len(multi_value_df) == original_len

    def test_string_atm_cols_converted_to_list(self, multi_value_df):
        result = atomize_by_column(multi_value_df, atm_cols="Hobbies", delimiter=",")
        assert len(result) == 6

    def test_column_with_no_delimiter_skipped(self, multi_value_df):
        result = atomize_by_column(multi_value_df, atm_cols=["Name"])
        assert len(result) == len(multi_value_df)


# ═══════════════════════════════════════════════════════════════════
#  atomize_by_row
# ═══════════════════════════════════════════════════════════════════

class TestAtomizeByRow:
    """Tests for row-wise atomization (splitting into columns)."""

    def test_basic_row_atomize(self):
        df = pd.DataFrame({
            "Name": ["Alice", "Bob"],
            "Scores": ["90,85,78", "72,68,91"],
        })
        result = atomize_by_row(df, atm_cols=["Scores"], delimiter=",")
        assert "Scores_1" in result.columns
        assert "Scores_2" in result.columns
        assert "Scores_3" in result.columns
        assert len(result) == 2

    def test_mismatched_field_count_skipped(self):
        """Rows with inconsistent field counts should be dropped."""
        df = pd.DataFrame({
            "Name": ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"],
            "Scores": [
                "90,85", "72,68", "80,75", "88,92", "70,65",
                "55,60", "78,83", "91,87", "67,72",
                "100",   # only J has 1 field instead of 2
            ],
        })
        result = atomize_by_row(df, atm_cols=["Scores"], delimiter=",")
        # J should be skipped since her field count doesn't match the mode (2)
        assert len(result) == 9
        assert "Scores_1" in result.columns
        assert "Scores_2" in result.columns

    def test_value_col_explicit(self):
        df = pd.DataFrame({
            "Name": ["Alice"],
            "Data": ["a,b,c"],
        })
        result = atomize_by_row(
            df, atm_cols=["Data"], delimiter=",", value_col="Data"
        )
        assert "Data_1" in result.columns

    def test_no_candidate_raises(self):
        df = pd.DataFrame({
            "Name": ["A", "B"],
            "Value": ["single", "cell"],
        })
        with pytest.raises(ValueError, match="No candidate"):
            atomize_by_row(df, atm_cols=["Value"], delimiter="|")

    def test_original_column_removed(self):
        df = pd.DataFrame({
            "Name": ["Alice"],
            "Scores": ["90,85"],
        })
        result = atomize_by_row(df, atm_cols=["Scores"], delimiter=",")
        assert "Scores" not in result.columns
        assert "Scores_1" in result.columns

    def test_tokens_are_stripped(self):
        df = pd.DataFrame({
            "Name": ["Alice"],
            "Data": [" a , b , c "],
        })
        result = atomize_by_row(
            df, atm_cols=["Data"], delimiter=",", value_col="Data"
        )
        assert result.iloc[0]["Data_1"] == "a"
        assert result.iloc[0]["Data_2"] == "b"


# ═══════════════════════════════════════════════════════════════════
#  isthere_header
# ═══════════════════════════════════════════════════════════════════

class TestIsthereHeader:
    """Tests for header detection heuristic."""

    def test_named_columns(self, clean_df):
        assert isthere_header(clean_df) is True

    def test_range_index(self):
        df = pd.DataFrame([[1, 2, 3], [4, 5, 6]])
        assert isthere_header(df) is False

    def test_unnamed_columns(self):
        df = pd.DataFrame({"Unnamed: 0": [1], "Unnamed: 1": [2]})
        assert isthere_header(df) is False

    def test_empty_df(self):
        assert isthere_header(pd.DataFrame()) is False

    def test_mixed_columns(self):
        """Some named, some unnamed — should return True."""
        df = pd.DataFrame({"Name": [1], "Unnamed: 1": [2]})
        # Not all columns are unnamed, so it's not purely unnamed
        assert isthere_header(df) is True

    def test_single_column_named(self):
        df = pd.DataFrame({"Count": [1, 2, 3]})
        assert isthere_header(df) is True

    def test_single_column_unnamed(self):
        df = pd.DataFrame({0: [1, 2, 3]})
        assert isthere_header(df) is False


# ═══════════════════════════════════════════════════════════════════
#  append
# ═══════════════════════════════════════════════════════════════════

class TestAppend:
    """Tests for DataFrame concatenation."""

    def test_matching_headers(self, clean_df):
        df2 = pd.DataFrame({"Name": ["Dave"], "Age": [35], "City": ["Gwangju"]})
        result = append(clean_df, df2)
        assert len(result) == 4

    def test_matching_headers_preserves_values(self, clean_df):
        df2 = pd.DataFrame({"Name": ["Dave"], "Age": [35], "City": ["Gwangju"]})
        result = append(clean_df, df2)
        assert "Dave" in result["Name"].values

    def test_extra_columns_in_df2(self, clean_df):
        df2 = pd.DataFrame({"Name": ["Dave"], "Age": [35], "City": ["X"], "Extra": [99]})
        result = append(clean_df, df2)
        assert len(result) == 4
        assert "Extra" not in result.columns  # reindexed to df1 columns

    def test_missing_columns_in_df2(self, clean_df):
        df2 = pd.DataFrame({"Name": ["Dave"]})  # missing Age, City
        result = append(clean_df, df2)
        assert len(result) == 4
        assert pd.isna(result.iloc[-1]["Age"])

    def test_no_header_mode(self, clean_df):
        df2 = pd.DataFrame([["Eve", 40, "Sejong"]])
        result = append(clean_df, df2, df2_header=False)
        assert len(result) == 4

    def test_no_header_fewer_cols(self, clean_df):
        df2 = pd.DataFrame([["Frank", 45]])
        result = append(clean_df, df2, df2_header=False)
        assert len(result) == 4
        assert pd.isna(result.iloc[-1]["City"])

    def test_no_header_more_cols(self, clean_df):
        df2 = pd.DataFrame([["Grace", 50, "Ulsan", "extra"]])
        result = append(clean_df, df2, df2_header=False)
        assert len(result) == 4

    def test_strict_mode_raises(self, clean_df):
        df2 = pd.DataFrame({"Name": ["X"], "NewCol": [99]})
        with pytest.raises(ValueError, match="strict"):
            append(clean_df, df2, strict=True)

    def test_strict_mode_passes_matching(self, clean_df):
        df2 = pd.DataFrame({"Name": ["X"], "Age": [1], "City": ["Y"]})
        result = append(clean_df, df2, strict=True)
        assert len(result) == 4

    def test_recover_types(self, clean_df):
        df2 = pd.DataFrame({"Name": ["X"], "Age": ["99"], "City": ["Y"]})
        result = append(clean_df, df2, recover_types=True, verbose=True)
        assert len(result) == 4

    def test_tuple_input(self, clean_df):
        df2 = pd.DataFrame({"Name": ["X"], "Age": [1], "City": ["Y"]})
        result = append((clean_df, {"info": 1}), (df2, {"info": 2}))
        assert len(result) == 4

    def test_auto_header_detection(self, clean_df):
        df2 = pd.DataFrame({"Name": ["X"], "Age": [1], "City": ["Y"]})
        result = append(clean_df, df2, df2_header="auto")
        assert len(result) == 4

    def test_multiple_appends(self, clean_df):
        """Chain multiple appends."""
        df2 = pd.DataFrame({"Name": ["D"], "Age": [1], "City": ["A"]})
        df3 = pd.DataFrame({"Name": ["E"], "Age": [2], "City": ["B"]})
        result = append(append(clean_df, df2), df3)
        assert len(result) == 5


# ═══════════════════════════════════════════════════════════════════
#  compare_structure
# ═══════════════════════════════════════════════════════════════════

class TestCompareStructure:
    """Tests for structure comparison."""

    def test_identical_structure(self, clean_df):
        result = compare_structure(clean_df, clean_df.copy())
        assert result["missing_in_df2"] == []
        assert result["extra_in_df2"] == []
        assert result["dtype_mismatch"] == {}

    def test_missing_columns(self, clean_df):
        df2 = clean_df.drop(columns=["City"])
        result = compare_structure(clean_df, df2)
        assert "City" in result["missing_in_df2"]

    def test_extra_columns(self, clean_df):
        df2 = clean_df.copy()
        df2["Extra"] = [1, 2, 3]
        result = compare_structure(clean_df, df2)
        assert "Extra" in result["extra_in_df2"]

    def test_dtype_mismatch(self):
        df1 = pd.DataFrame({"val": [1, 2, 3]})
        df2 = pd.DataFrame({"val": ["a", "b", "c"]})
        result = compare_structure(df1, df2)
        assert "val" in result["dtype_mismatch"]


# ═══════════════════════════════════════════════════════════════════
#  Merger
# ═══════════════════════════════════════════════════════════════════

class TestMerger:
    """Tests for row deduplication by summing."""

    def test_basic_merge(self):
        df = pd.DataFrame({"Cat": ["A", "A", "B"], "Value": [10, 20, 30]})
        result = merge(df, "Value")
        assert len(result) == 2
        assert result.loc[result["Cat"] == "A", "Value"].iloc[0] == 30

    def test_multiple_sum_columns(self, duplicate_rows_df):
        result = merge(duplicate_rows_df, ["Value1", "Value2"])
        assert len(result) < len(duplicate_rows_df)

    def test_sum_correct_values(self, duplicate_rows_df):
        result = merge(duplicate_rows_df, ["Value1", "Value2"])
        ax = result[(result["Category"] == "A") & (result["SubCat"] == "x")]
        assert ax["Value1"].iloc[0] == 30  # 10 + 20
        assert ax["Value2"].iloc[0] == 3.0  # 1.0 + 2.0

    def test_non_numeric_raises(self, clean_df):
        with pytest.raises(ValueError, match="must be numeric"):
            merge(clean_df, "Name")

    def test_string_sum_column_auto_list(self):
        df = pd.DataFrame({"Key": ["A", "A"], "Val": [1, 2]})
        result = merge(df, "Val")
        assert isinstance(result, pd.DataFrame)

    def test_no_duplicates_unchanged(self):
        df = pd.DataFrame({"Key": ["A", "B", "C"], "Val": [1, 2, 3]})
        result = merge(df, "Val")
        assert len(result) == 3

    def test_all_same_key(self):
        df = pd.DataFrame({"Key": ["X", "X", "X"], "Val": [10, 20, 30]})
        result = merge(df, "Val")
        assert len(result) == 1
        assert result.iloc[0]["Val"] == 60

    def test_all_columns_are_sum(self):
        """Edge case: every column is a sum column → no grouping keys."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        result = merge(df, ["A", "B"])
        assert result.iloc[0]["A"] == 3
        assert result.iloc[0]["B"] == 7

    def test_preserves_non_sum_columns(self, duplicate_rows_df):
        result = merge(duplicate_rows_df, "Value1")
        assert "Category" in result.columns
        assert "SubCat" in result.columns
        assert "Value2" in result.columns  # not a sum column, used as key


# ═══════════════════════════════════════════════════════════════════
#  Flattener — detect_header_end_col
# ═══════════════════════════════════════════════════════════════════

class TestDetectHeaderEndCol:
    """Tests for column-header boundary detection."""

    def test_with_wide_table(self):
        """Table with 1 row-header col and a wide numeric data block (≥80%)."""
        data = [
            ["Region", "Q1",  "Q2",  "Q3",  "Q4",  "Q5"],
            ["Seoul",  100,   120,   130,   110,   140],
            ["Busan",  80,    90,    100,   85,    95],
            ["Daegu",  60,    70,    75,    65,    80],
        ]
        df = pd.DataFrame(data)
        col = detect_header_end_col(df, header_rows=1)
        assert col == 1  # first column is the row header

    def test_requires_header_rows(self, wide_table_df):
        with pytest.raises(ValueError, match="header_rows must be specified"):
            detect_header_end_col(wide_table_df)

    def test_non_flattenable_raises(self):
        """A table with no numeric block should raise."""
        df = pd.DataFrame([
            ["a", "b", "c"],
            ["d", "e", "f"],
            ["g", "h", "i"],
        ])
        with pytest.raises(ValueError, match="not be flattenable"):
            detect_header_end_col(df, header_rows=1)


# ═══════════════════════════════════════════════════════════════════
#  flatten
# ═══════════════════════════════════════════════════════════════════

class TestFlatten:
    """Tests for multi-level header flattening."""

    def test_explicit_dims(self, wide_table_df):
        result = flatten(wide_table_df, header_rows=2, header_cols=2)
        assert "value" in result.columns
        assert len(result) > 0

    def test_correct_row_count(self, wide_table_df):
        result = flatten(wide_table_df, header_rows=2, header_cols=2)
        # 4 data rows × 4 data columns = 16 long-form rows
        assert len(result) == 16

    def test_custom_feature_names(self, wide_table_df):
        result = flatten(
            wide_table_df,
            header_rows=2,
            header_cols=2,
            vertical_feature_names=["region", "category"],
            horizontal_feature_names=["quarter", "metric"],
        )
        assert "region" in result.columns
        assert "category" in result.columns
        assert "quarter" in result.columns
        assert "metric" in result.columns

    def test_default_feature_names(self, wide_table_df):
        result = flatten(wide_table_df, header_rows=2, header_cols=2)
        assert "vertical_1" in result.columns
        assert "horizontal_1" in result.columns

    def test_custom_data_feature(self, wide_table_df):
        result = flatten(
            wide_table_df, header_rows=2, header_cols=2, data_feature="amount"
        )
        assert "amount" in result.columns
        assert "value" not in result.columns

    def test_3level_headers(self, wide_table_3level_df):
        result = flatten(wide_table_3level_df, header_rows=3, header_cols=1)
        assert len(result) > 0
        # Should have 3 horizontal columns
        horiz_cols = [c for c in result.columns if c.startswith("horizontal_")]
        assert len(horiz_cols) == 3

    def test_wrong_feature_name_count_fallback(self, wide_table_df):
        """If name count doesn't match levels, should use default names."""
        result = flatten(
            wide_table_df,
            header_rows=2,
            header_cols=2,
            vertical_feature_names=["only_one"],  # need 2
        )
        assert "vertical_1" in result.columns  # fell back to default

    def test_all_values_present(self, wide_table_df):
        """Spot-check: specific values should appear in the result."""
        result = flatten(wide_table_df, header_rows=2, header_cols=2)
        values = result["value"].tolist()
        assert "100" in values
        assert "155" in values


# ═══════════════════════════════════════════════════════════════════
#  Clarifier
# ═══════════════════════════════════════════════════════════════════

class TestClarifier:
    """Tests for dictionary-based value clarification."""

    def test_load_dictionary_from_file(self, dict_csv_path):
        if not os.path.exists(dict_csv_path):
            pytest.skip("Dict CSV not found")
        mapping = load_clarify_dictionary(dict_csv_path)
        assert len(mapping) > 0
        assert all(len(m) == 3 for m in mapping)

    def test_load_dictionary_from_temp(self, tmp_clarify_dict):
        mapping = load_clarify_dictionary(tmp_clarify_dict)
        assert len(mapping) > 0
        sources = [m[0] for m in mapping]
        assert "apple" in sources
        assert "APPLE" in sources

    def test_apply_mapping_replaces(self, tmp_clarify_dict):
        mapping = load_clarify_dictionary(tmp_clarify_dict)
        df = pd.DataFrame({"fruit": ["apple", "banana", "grape"]})
        result = apply_clarify_mapping(df, "fruit", mapping)
        assert result.iloc[0]["fruit"] == "FRUIT_APPLE"
        assert result.iloc[1]["fruit"] == "FRUIT_BANANA"

    def test_apply_mapping_keeps_unmapped(self, tmp_clarify_dict):
        mapping = load_clarify_dictionary(tmp_clarify_dict)
        df = pd.DataFrame({"fruit": ["apple", "UNKNOWN"]})
        result = apply_clarify_mapping(df, "fruit", mapping)
        assert result.iloc[1]["fruit"] == "UNKNOWN"  # unchanged

    def test_apply_mapping_addno_column(self, tmp_clarify_dict):
        mapping = load_clarify_dictionary(tmp_clarify_dict)
        df = pd.DataFrame({"fruit": ["apple", "cherry"]})
        result = apply_clarify_mapping(df, "fruit", mapping)
        assert "clarify_addno" in result.columns
        assert result.iloc[0]["clarify_addno"] == 1.0
        assert result.iloc[1]["clarify_addno"] == 2.0

    def test_apply_mapping_custom_addno_col(self, tmp_clarify_dict):
        mapping = load_clarify_dictionary(tmp_clarify_dict)
        df = pd.DataFrame({"fruit": ["apple"]})
        result = apply_clarify_mapping(df, "fruit", mapping, addno_col="weight")
        assert "weight" in result.columns

    def test_clarify_without_sum(self, tmp_clarify_dict):
        df = pd.DataFrame({"fruit": ["apple", "banana", "cherry"]})
        result = clarify(df, "fruit", tmp_clarify_dict)
        assert "clarify_addno" not in result.columns  # should be dropped
        assert result.iloc[0]["fruit"] == "FRUIT_APPLE"

    def test_clarify_with_sum_columns(self, tmp_clarify_dict):
        df = pd.DataFrame({
            "fruit": ["apple", "Apple", "banana"],
            "count": [10, 20, 5],
        })
        result = clarify(df, "fruit", tmp_clarify_dict, sum_columns=["count"])
        # apple & Apple both map to FRUIT_APPLE → should be merged
        apple_row = result[result["fruit"] == "FRUIT_APPLE"]
        assert len(apple_row) == 1
        # addno=1 for both, so sum = 10*1 + 20*1 = 30
        assert apple_row.iloc[0]["count"] == 30

    def test_clarify_addno_weight_applied(self, tmp_clarify_dict):
        """cherry has addno=2, so its count should be doubled."""
        df = pd.DataFrame({
            "fruit": ["cherry"],
            "count": [10],
        })
        result = clarify(df, "fruit", tmp_clarify_dict, sum_columns=["count"])
        assert result.iloc[0]["count"] == 20  # 10 * 2.0

    def test_clarify_empty_mapping(self, tmp_path):
        dict_df = pd.DataFrame({
            "target": pd.Series(dtype=str),
            "addno": pd.Series(dtype=float),
            "source1": pd.Series(dtype=str),
        })
        path = str(tmp_path / "empty_dict.csv")
        dict_df.to_csv(path, index=False)
        df = pd.DataFrame({"col": ["a", "b"]})
        result = clarify(df, "col", path)
        assert list(result["col"]) == ["a", "b"]  # unchanged

    def test_case_sensitive_mapping(self, tmp_clarify_dict):
        mapping = load_clarify_dictionary(tmp_clarify_dict)
        df = pd.DataFrame({"fruit": ["apple", "Apple", "APPLE", "aPpLe"]})
        result = apply_clarify_mapping(df, "fruit", mapping)
        assert result.iloc[0]["fruit"] == "FRUIT_APPLE"  # matches source1
        assert result.iloc[1]["fruit"] == "FRUIT_APPLE"  # matches source2
        assert result.iloc[2]["fruit"] == "FRUIT_APPLE"  # matches source3
        assert result.iloc[3]["fruit"] == "aPpLe"        # no match → unchanged


# ═══════════════════════════════════════════════════════════════════
#  Top-level package imports
# ═══════════════════════════════════════════════════════════════════

class TestPackageImports:
    """Verify that the public API is importable from the top-level package."""

    def test_import_parse(self):
        from pynorma import parse
        assert callable(parse)

    def test_import_save_dataframe(self):
        from pynorma import save_dataframe
        assert callable(save_dataframe)

    def test_import_flatten(self):
        from pynorma import flatten
        assert callable(flatten)

    def test_import_atomize_by_column(self):
        from pynorma import atomize_by_column
        assert callable(atomize_by_column)

    def test_import_atomize_by_row(self):
        from pynorma import atomize_by_row
        assert callable(atomize_by_row)

    def test_import_clarify(self):
        from pynorma import clarify
        assert callable(clarify)

    def test_import_append(self):
        from pynorma import append
        assert callable(append)

    def test_import_merge(self):
        from pynorma import merge
        assert callable(merge)

    def test_version(self):
        import pynorma
        assert hasattr(pynorma, "__version__")
        assert isinstance(pynorma.__version__, str)
        assert len(pynorma.__version__) > 0

    def test_all_exports(self):
        import pynorma
        assert hasattr(pynorma, "__all__")
        assert set(pynorma.__all__) == {
            "parse", "save_dataframe", "flatten",
            "atomize_by_column", "atomize_by_row", "detect_multivalue_columns",
            "clarify", "append", "merge", "Pipeline",
        }
