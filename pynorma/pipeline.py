"""
pipeline.py — Full PyNorma pipeline: Detection → DataFrame → Preprocessor.

Bridge connecting the ensemble TableRegion detection system to the existing
preprocessor modules (atomizer, clarifier, merger, flattener, appender).

Usage:
    import pynorma
    from pynorma.pipeline import Pipeline

    # Simple — parse + detect + clean in one call
    df = Pipeline("data.csv").run()

    # Full control
    p = Pipeline("data.xlsx", strategy="D")
    p.detect()                     # Phase 1: find tables
    p.clean()                      # Phase 2: clean within regions
    p.atomize(cols=["Tags"])       # Phase 3: explode multi-valued cells
    p.clarify("업종", dict_path)   # Phase 4: standardize values
    p.merge(sum_columns=["매출"])  # Phase 5: deduplicate
    df = p.result()
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Union, List

import pandas as pd

logger = logging.getLogger("pynorma")

# Lazy imports to avoid circular deps at module level
_DETECT_AVAILABLE = True  # Will be checked on first use


def _import_detection():
    """Import the in-package detection engine (``pynorma.detect``)."""
    try:
        from pynorma.detect import core as bcore
        from pynorma.detect.preprocess import detect as ensemble_detect
        return {
            "TableRegion": bcore.TableRegion,
            "quality_score": bcore.quality_score,
            "clean_region": bcore.clean_region,
            "read_specimen": bcore.read_specimen,
            "detect": ensemble_detect,
            "build_table_model": bcore.build_table_model,
            "clean_region_model": bcore.clean_region_model,
            "to_long": bcore.to_long,
            "model_to_region": bcore.model_to_region,
        }
    except ImportError:
        return None


class Pipeline:
    """Full PyNorma pipeline: Detection → DataFrame → Preprocessor.

    Parameters
    ----------
    source : str or Path or pd.DataFrame
        File path or pre-loaded DataFrame.
    strategy : str, optional
        Detection strategy: "A"~"F" or None (run-all auto-select).
    sheet_name : str or int, optional
        For XLSX files, which sheet to read.

    Examples
    --------
    >>> df = Pipeline("messy_data.csv").run()
    >>> df = Pipeline("report.xlsx", strategy="D").run()
    """

    def __init__(
        self,
        source: Union[str, Path, pd.DataFrame],
        *,
        strategy: Optional[str] = None,
        sheet_name: Optional[Union[str, int]] = None,
    ):
        self._source = source
        self._strategy = strategy
        self._sheet_name = sheet_name
        self._df: Optional[pd.DataFrame] = None
        self._tables: list[pd.DataFrame] = []
        self._regions = []
        self._models = []
        self._grid = None
        self._log: list[str] = []

    # ──────────────────────────────────────
    # Phase 1: Detection
    # ──────────────────────────────────────

    def detect(self) -> "Pipeline":
        """Detect table regions using ensemble strategies.

        Uses the benchmark TableRegion system with quality_score
        auto-selection when no strategy is specified.
        """
        modules = _import_detection()

        if modules is None:
            # Fallback: use pynorma.parse() without ensemble detection
            self._log.append("Detection: fallback to pynorma.parse()")
            from pynorma.io.parser import parse
            path = str(self._source) if isinstance(self._source, (str, Path)) else None
            if path:
                self._df = parse(path, sheet_name=self._sheet_name)
                self._tables = [self._df]
            elif isinstance(self._source, pd.DataFrame):
                self._df = self._source
                self._tables = [self._df]
            return self

        if isinstance(self._source, pd.DataFrame):
            # Convert DataFrame to grid for detection
            grid = [list(self._source.columns)] + self._source.values.tolist()
            grid = [[str(c) if c is not None else "" for c in row] for row in grid]
        else:
            grid, _ = modules["read_specimen"](Path(self._source), sheet=self._sheet_name)

        self._grid = grid
        raw_regions = modules["detect"](grid, strategy=self._strategy)
        self._models = [modules["build_table_model"](grid, r) for r in raw_regions]
        # Report the structurally-refined regions (correct header row, data
        # top/bottom, headerless detection) rather than the coarse ensemble
        # output — the model is a strictly better structural estimate.
        self._regions = [modules["model_to_region"](grid, m) for m in self._models]

        self._log.append(
            f"Detection: {len(self._regions)} table(s) found "
            f"(strategy={'auto' if not self._strategy else self._strategy})"
        )

        return self

    # ──────────────────────────────────────
    # Phase 2: Cleaning
    # ──────────────────────────────────────

    def clean(self) -> "Pipeline":
        """Apply common cleaning pipeline to detected regions.

        Converts each detected TableRegion into a clean pd.DataFrame.
        """
        modules = _import_detection()

        if not self._regions or not self._grid or modules is None:
            if self._df is not None:
                self._tables = [self._df]
            self._log.append("Clean: using existing DataFrame (no regions)")
            return self

        self._tables = []
        for i, region in enumerate(self._regions):
            if i < len(self._models):
                model = self._models[i]
                cleaned_rows = modules["clean_region_model"](self._grid, model)
                desc = (f"header_rows={model.header_rows}, stub_end={model.stub_end}, "
                        f"rows=[{model.top}..{model.bottom}], "
                        f"cols=[{model.left}..{model.right})")
            else:
                cleaned_rows = modules["clean_region"](self._grid, region)
                desc = (f"header={region.header}, "
                        f"rows=[{region.top}..{region.bottom}], "
                        f"cols=[{region.left}..{region.right})")
            if cleaned_rows and len(cleaned_rows) >= 2:
                header = cleaned_rows[0]
                data = cleaned_rows[1:]
                df = pd.DataFrame(data, columns=header)
                self._tables.append(df)
                self._log.append(
                    f"Clean: table {i} → {df.shape[0]} rows × {df.shape[1]} cols ({desc})"
                )

        if self._tables:
            self._df = self._tables[0]

        return self

    # ──────────────────────────────────────
    # Phase 3: Atomize
    # ──────────────────────────────────────

    def atomize(
        self,
        cols: Optional[Union[str, List[str]]] = None,
        delimiter: Optional[str] = None,
        mode: str = "column",
    ) -> "Pipeline":
        """Atomize multi-valued cells (1NF normalization).

        Parameters
        ----------
        cols : str or list of str, optional
            Columns to atomize. None=auto-detect.
        delimiter : str, optional
            In-cell delimiter. None=auto-detect.
        mode : "column" or "row"
            "column" = explode (more rows),
            "row" = split (more columns).
        """
        from pynorma.preprocessor.atomizer import atomize_by_column, atomize_by_row

        if self._df is None:
            return self

        if mode == "column":
            self._df = atomize_by_column(self._df, atm_cols=cols, delimiter=delimiter)
            self._log.append(f"Atomize (column): {self._df.shape}")
        else:
            self._df = atomize_by_row(
                self._df, atm_cols=cols or [], delimiter=delimiter
            )
            self._log.append(f"Atomize (row): {self._df.shape}")

        return self

    # ──────────────────────────────────────
    # Phase 4: Clarify
    # ──────────────────────────────────────

    def clarify(
        self,
        column: str,
        dict_path: str,
        sum_columns: Optional[List[str]] = None,
    ) -> "Pipeline":
        """Standardize column values using a dictionary mapping.

        Parameters
        ----------
        column : str
            Column to standardize.
        dict_path : str
            Path to clarification dictionary CSV.
        sum_columns : list of str, optional
            Numeric columns to aggregate when merging duplicates.
        """
        from pynorma.preprocessor.clarifier import clarify

        if self._df is None:
            return self

        self._df = clarify(self._df, column, dict_path, sum_columns=sum_columns)
        self._log.append(f"Clarify: column='{column}', shape={self._df.shape}")

        return self

    # ──────────────────────────────────────
    # Phase 5: Merge
    # ──────────────────────────────────────

    def merge(self, sum_columns: Union[str, List[str]]) -> "Pipeline":
        """Deduplicate rows by summing numeric columns.

        Parameters
        ----------
        sum_columns : str or list of str
            Numeric columns to aggregate.
        """
        from pynorma.preprocessor.merger import merge

        if self._df is None:
            return self

        self._df = merge(self._df, sum_column=sum_columns)
        self._log.append(f"Merge: shape={self._df.shape}")

        return self

    # ──────────────────────────────────────
    # Phase 6: Long-form conversion
    # ──────────────────────────────────────

    def to_long(
        self,
        table_index: int = 0,
        *,
        value_name: str = "value",
        dropna: bool = True,
        ffill_stub: bool = True,
    ) -> "Pipeline":
        """Convert a detected table into long form via its TableModel.

        Deterministic melt driven by the detected structure (multi-row header
        block + stub columns). Requires .detect() to have run; this is the
        primary path for the project goal "any tabular data → long form".
        """
        modules = _import_detection()

        if modules is None or not self._models or table_index >= len(self._models):
            # No structural model available — fall back to legacy flattener
            return self.flatten()

        columns, rows = modules["to_long"](
            self._grid,
            self._models[table_index],
            value_name=value_name,
            dropna=dropna,
            ffill_stub=ffill_stub,
        )
        self._df = pd.DataFrame(rows, columns=columns)
        self._log.append(f"ToLong: table {table_index} → shape={self._df.shape}")

        return self

    def flatten(self, **kwargs) -> "Pipeline":
        """Convert wide multi-level header table into tidy long format.

        When a TableModel is available (after .detect()), delegates to
        model-driven to_long(); the legacy DataFrame-based flattener runs
        only when there is no detected structure to rely on.
        """
        if self._models and self._grid is not None:
            return self.to_long()

        from pynorma.preprocessor.flattener import flatten

        if self._df is None:
            return self

        self._df = flatten(self._df, **kwargs)
        self._log.append(f"Flatten: shape={self._df.shape}")

        return self

    # ──────────────────────────────────────
    # Phase 7: Append
    # ──────────────────────────────────────

    def append_table(self, other: Union[pd.DataFrame, int] = 1) -> "Pipeline":
        """Append another detected table or an external DataFrame.

        Parameters
        ----------
        other : pd.DataFrame or int
            If int, appends the Nth detected table (0-indexed).
            If DataFrame, appends it directly.
        """
        from pynorma.preprocessor.appender import append

        if self._df is None:
            return self

        if isinstance(other, int) and other < len(self._tables):
            self._df = append(self._df, self._tables[other])
            self._log.append(f"Append: merged table {other}")
        elif isinstance(other, pd.DataFrame):
            self._df = append(self._df, other)
            self._log.append("Append: merged external DataFrame")

        return self

    # ──────────────────────────────────────
    # Output
    # ──────────────────────────────────────

    def result(self, table_index: int = 0) -> pd.DataFrame:
        """Return the processed DataFrame.

        Parameters
        ----------
        table_index : int
            Which table to return (when multiple detected).
        """
        if self._df is not None:
            return self._df
        if table_index < len(self._tables):
            return self._tables[table_index]
        raise ValueError("No processed table available. Call .detect().clean() first.")

    def all_tables(self) -> list[pd.DataFrame]:
        """Return all detected tables as a list of DataFrames."""
        return self._tables

    @property
    def log(self) -> list[str]:
        """Return processing log."""
        return list(self._log)

    def run(self, shape: str = "wide") -> pd.DataFrame:
        """Convenience: detect + clean (+ long-form conversion) in one call.

        Parameters
        ----------
        shape : "wide" or "long"
            "wide" (default) returns the cleaned table as-is.
            "long" additionally melts it into long form via the detected
            TableModel structure.
        """
        self.detect().clean()
        if shape == "long":
            self.to_long()
        return self.result()

    def save(self, path: str, table_index: int = 0, **kwargs) -> None:
        """Save result to file."""
        from pynorma.io.writer import save_dataframe
        save_dataframe(self.result(table_index), path, **kwargs)

    def __repr__(self) -> str:
        n = len(self._tables)
        shape = self._df.shape if self._df is not None else "None"
        return f"Pipeline(tables={n}, current_shape={shape})"
