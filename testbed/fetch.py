"""
testbed/fetch.py — Reproducibly (re)build the testbed data pool.

The raw CSV/XLSX files are NOT committed to the repo (see .gitignore → /testbed/data/).
Only this *source* — the URL list + build logic — plus the ground-truth labels in
manifest.json are tracked. Run this to reconstruct testbed/data/ from scratch:

    python testbed/fetch.py            # build everything
    python testbed/fetch.py --report   # just re-emit the build report for existing files

What it does:
  1. Ensures the synthetic + previously-collected specimens exist by running the
     existing (deterministic, seed=42) collectors in specimen/, then copies the
     curated subset into testbed/data/{synthetic,real}/.
  2. Downloads the NEWLY curated reference datasets (NEW_SOURCES) directly, with
     the same sanitization used across the project (CSV formula-injection neutralized,
     null bytes / BOM stripped, binary/oversize rejected, XLSX signature checked).
  3. Writes testbed/data/_build_report.json with sha256 / bytes / rows / cols for
     every file, so manifest.json can pin expected content and drift is detectable.

Security: downloads are capped at 5 MB, verified against binary/executable signatures,
and CSV cells beginning with = + - @ are prefixed with ' to defuse spreadsheet formula
injection. XLSX are accepted only with a PK ZIP signature (macros live in .xlsm, not .xlsx).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

TESTBED_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTBED_DIR.parent
SPECIMEN_DIR = PROJECT_ROOT / "specimen"
DATA_DIR = TESTBED_DIR / "data"
REAL_DIR = DATA_DIR / "real"
SYN_DIR = DATA_DIR / "synthetic"

MAX_DOWNLOAD_SIZE = 5 * 1024 * 1024
DOWNLOAD_TIMEOUT = 20
HEADERS = {"User-Agent": "Mozilla/5.0 (PyNorma-Testbed-Fetch/1.0)"}

if str(SPECIMEN_DIR) not in sys.path:
    sys.path.insert(0, str(SPECIMEN_DIR))


# ══════════════════════════════════════════════════════════════
# Source lists
# ══════════════════════════════════════════════════════════════

# (testbed_name, specimen_filename)  — synthetic, generated deterministically.
FROM_SPECIMEN_SYNTHETIC = [
    ("01_messy_sales", "01_messy_sales.csv"),
    ("02_multiheader_report", "02_multiheader_report.csv"),
    ("03_encoding_chaos", "03_encoding_chaos.csv"),
    ("04_ragged_columns", "04_ragged_columns.csv"),
    ("05_merged_cells_mess", "05_merged_cells_mess.xlsx"),
    ("06_pivot_style_table", "06_pivot_style_table.csv"),
    ("07_semicolon_european", "07_semicolon_european.csv"),
    ("08_annotated_stats_table", "08_annotated_stats_table.xlsx"),
    ("09_wide_sparse", "09_wide_sparse.csv"),
    ("10_multiple_tables_one_sheet", "10_multiple_tables_one_sheet.xlsx"),
    ("11_no_header_numeric", "11_no_header_numeric.csv"),
    ("12_deep_multiheader", "12_deep_multiheader.csv"),
    ("13_pivot_crosstab", "13_pivot_crosstab.csv"),
    ("14_three_tables_gapped", "14_three_tables_gapped.csv"),
    ("15_subtotals_interspersed", "15_subtotals_interspersed.csv"),
    ("16_extreme_sparse", "16_extreme_sparse.csv"),
    ("17_crosstab_rowheaders", "17_crosstab_rowheaders.csv"),
    ("18_empty_cols_middle", "18_empty_cols_middle.csv"),
    ("19_title_footnotes_heavy", "19_title_footnotes_heavy.csv"),
    ("20_mixed_lang_units", "20_mixed_lang_units.csv"),
    ("21_extreme_ragged", "21_extreme_ragged.csv"),
    ("22_single_column", "22_single_column.csv"),
]

# (testbed_name, specimen_filename) — real files already collected by specimen scripts.
FROM_SPECIMEN_REAL = [
    ("realworld_cyclones_philippines", "realworld_cyclones_philippines.xlsx"),
    ("realworld_occupational_health", "realworld_occupational_health.xlsx"),
    ("realworld_population_deaths", "realworld_population_deaths.xlsx"),
    ("realworld_vaccine_study", "realworld_vaccine_study.xlsx"),
    ("realworld_ihtm_survey_2025", "realworld_ihtm_survey_2025.xlsx"),
    ("realworld_healthcare_messy", "realworld_healthcare_messy.csv"),
    ("realworld_hr_messy", "realworld_hr_messy.csv"),
    ("realworld_warehouse_messy", "realworld_warehouse_messy.csv"),
    ("realworld_imdb_messy", "realworld_imdb_messy.csv"),
    ("realworld_automobile", "realworld_automobile.csv"),
    ("realworld_datascience_jobs_uncleaned", "realworld_datascience_jobs_uncleaned.csv"),
    ("diabetes_missing_data", "diabetes_missing_data.csv"),
    ("github_messy_data", "github_messy_data.csv"),
    ("global_world_cities", "global_world_cities.csv"),
]

# Newly curated reference datasets (from the testbed source-discovery workflow).
# GitHub raw URLs are pinned to a commit SHA for reproducibility.
# Each: {"name","url","format"("csv"|"xlsx"|"tsv"),"encoding"(opt),"delimiter"(opt)}.
NEW_SOURCES: list[dict] = [
    # ── Classic ML datasets with real missingness ──
    {"name": "uci_adult_census", "format": "csv",
     "url": "https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data"},
    {"name": "seaborn_titanic", "format": "csv",
     "url": "https://raw.githubusercontent.com/mwaskom/seaborn-data/a29a0141d20e156043ec257a64c8de3b3a03fd6e/titanic.csv"},
    {"name": "seaborn_penguins", "format": "csv",
     "url": "https://raw.githubusercontent.com/mwaskom/seaborn-data/4e06bf0b8c4bf161ed04e9df59b77c35fd2ec44a/penguins.csv"},

    # ── Tidy-data canonical "untidy" sets (Wickham / tidyr) ──
    {"name": "tidy_relig_income_pew", "format": "csv",
     "url": "https://raw.githubusercontent.com/tidyverse/tidyr/11572d8c5588e46865efc26b0de6f4b4f0a23815/data-raw/relig_income.csv"},
    {"name": "tidy_billboard_wide", "format": "csv", "encoding": "latin-1",
     "url": "https://raw.githubusercontent.com/hadley/tidy-data/25dd834ba47b098d3894481078137b5962c2f942/data/billboard.csv"},
    {"name": "tidy_weather_wide", "format": "csv",
     "url": "https://raw.githubusercontent.com/tidyverse/tidyr/2c35387d4dea6fb5d725ec41b428341a20dcc7ac/vignettes/weather.csv"},
    {"name": "tidy_us_rent_income", "format": "csv",
     "url": "https://raw.githubusercontent.com/tidyverse/tidyr/36502c811832319821d40aafed56d58d1549166a/data-raw/us_rent_income.csv"},
    {"name": "tidy_table4a_pivot", "format": "csv",
     "url": "https://raw.githubusercontent.com/tidyverse/tidyr/4fb915d7143c28bcaee6ed7e2b8628c33ba2b069/data-raw/table4a.csv"},

    # ── Government / statistical multi-header XLSX ──
    {"name": "census_h1_income_limits", "format": "xlsx",
     "url": "https://raw.githubusercontent.com/rfordatascience/tidytuesday/714c6d44b6c56715eb8f94f82b24d02dade7e113/data/2021/2021-02-09/h01a.xlsx"},
    {"name": "bls_cps_occupation_by_industry_2015", "format": "xlsx",
     "url": "https://raw.githubusercontent.com/rfordatascience/tidytuesday/428166c724b884f0a9afcc87c4552a0ad2726c2d/data/2021/2021-02-23/bls-2015.xlsx"},
    {"name": "nces_educational_attainment_104_10", "format": "xlsx",
     "url": "https://raw.githubusercontent.com/rfordatascience/tidytuesday/184779aada0363db28cdeff6c47a3655b40879d9/data/2021/2021-02-02/104.10.xlsx"},
    {"name": "nea_artists_in_workforce_table1a", "format": "xlsx",
     "url": "https://raw.githubusercontent.com/rfordatascience/tidytuesday/f55f1f30735a689efa3de1877b9d641d934eaf0f/data/2022/2022-09-27/ADP-31-artists-in-the-workforce-NationalTablesv2/Table1aArtistProfile.xlsx"},

    # ── Known dirty / messy teaching datasets ──
    {"name": "dat8_chipotle_orders", "format": "tsv",
     "url": "https://raw.githubusercontent.com/justmarkham/DAT8/7dda003ffa795664e603868d6077e00974d61d0d/data/chipotle.tsv"},
    {"name": "tidyr_who_tb", "format": "csv",
     "url": "https://raw.githubusercontent.com/tidyverse/tidyr/36502c811832319821d40aafed56d58d1549166a/data-raw/who.csv"},
    {"name": "tidytuesday_coffee_ratings", "format": "csv",
     "url": "https://raw.githubusercontent.com/rfordatascience/tidytuesday/f2b0b31e316d0e35eef4834b9b058d05d46ffadf/data/2020/2020-07-07/coffee_ratings.csv"},
    {"name": "tidytuesday_us_avg_tuition", "format": "xlsx",
     "url": "https://raw.githubusercontent.com/rfordatascience/tidytuesday/362fa86c328797428736f05c22af5eca3a27b731/data/2018/2018-04-02/us_avg_tuition.xlsx"},

    # ── 1NF-violation / multi-valued cells ──
    {"name": "movielens_movies", "format": "csv",
     "url": "https://raw.githubusercontent.com/nchah/movielens-recommender/4c1a69e092bca937f8ef029f4747e8a247678253/data/ml-movies.csv"},
    {"name": "netflix_titles", "format": "csv",
     "url": "https://raw.githubusercontent.com/rfordatascience/tidytuesday/f55f1f30735a689efa3de1877b9d641d934eaf0f/data/2021/2021-04-20/netflix_titles.csv"},
    {"name": "goodbooks_books", "format": "csv",
     "url": "https://raw.githubusercontent.com/zygmuntz/goodbooks-10k/fdb21c94e9e6e3340966a231c5bda91466e61ed6/books.csv"},
]


# ══════════════════════════════════════════════════════════════
# Sanitization / safety
# ══════════════════════════════════════════════════════════════

def sanitize_csv_cell(value: str) -> str:
    if isinstance(value, str):
        value = value.replace("\x00", "").replace("﻿", "")
        if value and value[0] in ("=", "+", "-", "@", "\t", "\r", "\n"):
            value = "'" + value
    return value


def sanitize_csv_bytes(raw: bytes, encoding: str, delimiter: str = ",") -> str:
    """Neutralize formula injection cell-by-cell, preserving the source delimiter."""
    text = raw.decode(encoding, errors="replace")
    out = io.StringIO()
    w = csv.writer(out, delimiter=delimiter)
    for row in csv.reader(io.StringIO(text), delimiter=delimiter):
        w.writerow([sanitize_csv_cell(c) for c in row])
    return out.getvalue()


def is_xlsx_signature(raw: bytes) -> bool:
    return raw[:4] == b"\x50\x4b\x03\x04"


def is_dangerous_binary(raw: bytes) -> bool:
    return any(raw[:len(s)] == s for s in (b"\x4d\x5a", b"\x7fELF", b"\xd0\xcf\x11\xe0"))


def _download(url: str) -> bytes | None:
    old = socket.getdefaulttimeout()
    socket.setdefaulttimeout(DOWNLOAD_TIMEOUT)
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT) as resp:
            chunks, total = [], 0
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_DOWNLOAD_SIZE:
                    print(f"    ⚠ exceeds {MAX_DOWNLOAD_SIZE:,} bytes — skipped")
                    return None
                chunks.append(chunk)
        return b"".join(chunks)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
            socket.timeout, ConnectionError, OSError) as e:
        print(f"    ✗ download failed: {e}")
        return None
    finally:
        socket.setdefaulttimeout(old)


# ══════════════════════════════════════════════════════════════
# Fingerprinting
# ══════════════════════════════════════════════════════════════

def fingerprint(path: Path) -> dict:
    """sha256 / bytes / rows / cols / encoding / delimiter via pynorma's own reader."""
    from pynorma.detect.core import read_specimen, grid_cols
    raw = path.read_bytes()
    info = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    try:
        grid, meta = read_specimen(path)
        info.update(rows=len(grid), cols=grid_cols(grid),
                    encoding=meta.get("encoding"), delimiter=meta.get("delimiter"))
    except Exception as e:  # noqa: BLE001
        info["read_error"] = f"{type(e).__name__}: {e}"
    return info


# ══════════════════════════════════════════════════════════════
# Build steps
# ══════════════════════════════════════════════════════════════

def ensure_specimens() -> None:
    """Run the deterministic specimen collectors so the source pool exists."""
    scripts = ["_collect_specimens.py", "_generate_adversarial.py", "_collect_realworld.py"]
    for s in scripts:
        path = SPECIMEN_DIR / s
        if not path.exists():
            print(f"  ⚠ {s} not found — skipping")
            continue
        print(f"  ▶ running specimen/{s} …")
        try:
            subprocess.run([sys.executable, str(path)], cwd=str(SPECIMEN_DIR),
                           check=False, capture_output=True, timeout=300)
        except Exception as e:  # noqa: BLE001
            print(f"    ⚠ {s}: {e}")


def copy_from_specimen(pairs, dest_dir: Path, report: dict, kind: str) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    for name, fname in pairs:
        src = SPECIMEN_DIR / fname
        if not src.exists():
            print(f"  ⏭ {name}: source {fname} missing (specimen collector failed?)")
            continue
        ext = src.suffix.lower()
        dst = dest_dir / f"{name}{ext}"
        dst.write_bytes(src.read_bytes())
        fp = fingerprint(dst)
        report[name] = {"file": f"{kind}/{dst.name}", "kind": kind, "origin": "specimen",
                        "specimen_file": fname, **fp}
        print(f"  ✓ {name:42s} {fp.get('rows','?')}×{fp.get('cols','?')}  ({fp['bytes']:,} b)")


def download_new(sources, report: dict) -> None:
    REAL_DIR.mkdir(parents=True, exist_ok=True)
    for src in sources:
        name, url, fmt = src["name"], src["url"], src.get("format", "csv")
        print(f"\n  → {name}\n    {url}")
        raw = _download(url)
        if raw is None:
            continue
        if is_dangerous_binary(raw):
            print("    ⚠ dangerous binary signature — skipped")
            continue
        # NB: pynorma's reader dispatches on extension and only knows .csv/.xlsx,
        # but its delimiter auto-detection handles tabs — so TSV content is stored
        # with a .csv extension (tab-delimited) to stay readable by the Pipeline.
        ext = ".xlsx" if fmt == "xlsx" else ".csv"
        dst = REAL_DIR / f"{name}{ext}"
        if fmt == "xlsx":
            if not is_xlsx_signature(raw):
                print("    ⚠ not a valid XLSX (no PK signature) — skipped")
                continue
            dst.write_bytes(raw)
        else:
            enc = src.get("encoding", "utf-8")
            delim = "\t" if fmt == "tsv" else src.get("delimiter", ",")
            dst.write_text(sanitize_csv_bytes(raw, enc, delim), encoding="utf-8")
        fp = fingerprint(dst)
        report[name] = {"file": f"real/{dst.name}", "kind": "real", "origin": "download",
                        "url": url, **fp}
        print(f"    ✓ {fp.get('rows','?')}×{fp.get('cols','?')}  ({fp['bytes']:,} b)  "
              f"sha={fp['sha256'][:12]}")


# ══════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", action="store_true",
                    help="Only re-fingerprint existing data/ files (no download).")
    ap.add_argument("--skip-specimens", action="store_true",
                    help="Do not re-run the specimen collectors (use existing files).")
    args = ap.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    report: dict = {}

    if args.report:
        for d, kind in ((SYN_DIR, "synthetic"), (REAL_DIR, "real")):
            for f in sorted(d.glob("*")):
                if f.is_file():
                    report[f.stem] = {"file": f"{kind}/{f.name}", "kind": kind, **fingerprint(f)}
    else:
        print("═" * 70)
        print("  PyNorma Testbed — building data pool")
        print("═" * 70)
        if not args.skip_specimens:
            print("\n[1/3] Ensuring specimen source pool …")
            ensure_specimens()
        print("\n[2/3] Copying curated specimens → testbed/data/ …")
        copy_from_specimen(FROM_SPECIMEN_SYNTHETIC, SYN_DIR, report, "synthetic")
        copy_from_specimen(FROM_SPECIMEN_REAL, REAL_DIR, report, "real")
        print(f"\n[3/3] Downloading {len(NEW_SOURCES)} new reference datasets …")
        download_new(NEW_SOURCES, report)

    out = DATA_DIR / "_build_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n📦 {len(report)} files in testbed/data/  →  build report: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
