"""
Command-line interface for PyNorma.

Requires the optional ``[cli]`` extra (``pip install "pynorma[cli]"``). Exposed
as the ``pynorma`` console script and via ``python -m pynorma``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

try:
    import typer
except ModuleNotFoundError:  # pragma: no cover - guidance when the extra is absent
    raise SystemExit(
        'The PyNorma CLI needs extra dependencies. Install them with:\n'
        '    pip install "pynorma[cli]"'
    )

from pynorma import __version__
from pynorma.pipeline import Pipeline

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="PyNorma — turn messy spreadsheets into clean, tidy tables.",
)


def _write(df, output: Path) -> None:
    """Write a DataFrame to CSV or XLSX based on the output extension."""
    if output.suffix.lower() in (".xlsx", ".xls"):
        df.to_excel(output, index=False)
    else:
        df.to_csv(output, index=False)


def _parse_sheet(sheet):
    """Parse a --sheet value as a 0-based index or a worksheet name."""
    if sheet is None:
        return None
    return int(sheet) if sheet.lstrip("-").isdigit() else sheet


@app.command()
def clean(
    input: Path = typer.Argument(
        ..., exists=True, dir_okay=False, readable=True,
        help="Messy CSV/XLSX file to clean.",
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Write the result to this .csv/.xlsx. If omitted, prints a preview.",
    ),
    strategy: Optional[str] = typer.Option(
        None, "--strategy", "-s",
        help="Detection strategy A-F. Omit to auto-select (recommended).",
    ),
    sheet: Optional[str] = typer.Option(
        None, "--sheet",
        help="XLSX worksheet name or 0-based index (default: auto).",
    ),
    shape: str = typer.Option(
        "wide", "--shape",
        help="'wide' (default) or 'long' (tidy melt of the detected structure).",
    ),
    table: int = typer.Option(
        0, "--table", "-t",
        help="Which detected table to output, 0-based (for multi-table sheets).",
    ),
):
    """Detect and clean the table(s) in a messy file."""
    if shape not in ("wide", "long"):
        raise typer.BadParameter("--shape must be 'wide' or 'long'")

    p = Pipeline(
        str(input), strategy=strategy.upper() if strategy else None,
        sheet_name=_parse_sheet(sheet),
    ).detect().clean()
    tables = p.all_tables()
    if not tables:
        typer.echo(f"No table detected in {input.name}.", err=True)
        raise typer.Exit(1)
    if not 0 <= table < len(tables):
        raise typer.BadParameter(
            f"--table {table} out of range (found {len(tables)} table(s))"
        )

    if shape == "long":
        p.to_long(table)
        df = p.result()
    else:
        df = tables[table]

    if output is None:
        typer.echo(df.head(20).to_string(index=False))
        typer.echo(
            f"\n[{df.shape[0]} rows x {df.shape[1]} cols] preview — pass -o to save."
        )
    else:
        _write(df, output)
        typer.echo(f"Wrote {df.shape[0]} x {df.shape[1]} -> {output}")


@app.command()
def detect(
    input: Path = typer.Argument(
        ..., exists=True, dir_okay=False, readable=True,
        help="CSV/XLSX file to inspect.",
    ),
    sheet: Optional[str] = typer.Option(
        None, "--sheet",
        help="XLSX worksheet name or 0-based index (default: auto).",
    ),
):
    """Report the detected table region(s) without writing any output."""
    p = Pipeline(str(input), sheet_name=_parse_sheet(sheet)).detect().clean()
    tables = p.all_tables()
    typer.echo(f"{len(tables)} table(s) detected in {input.name}:")
    for i, t in enumerate(tables):
        cols = ", ".join(map(str, list(t.columns)[:8]))
        more = " …" if t.shape[1] > 8 else ""
        typer.echo(f"  [{i}] {t.shape[0]} rows x {t.shape[1]} cols — {cols}{more}")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"pynorma {__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True,
        help="Show the version and exit.",
    ),
):
    """PyNorma command-line interface."""


def main() -> None:
    """Console-script entry point."""
    app()


if __name__ == "__main__":
    main()
