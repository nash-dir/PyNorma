# PyNorma Testbed

A **benchmark-reference testbed** for PyNorma's messy-table detection and cleaning.
It holds a curated corpus of deliberately messy CSV/XLSX files — each with a
**human-verified ground-truth label** — and a runner that scores the *shipping*
`pynorma.Pipeline` against those labels.

> **How this differs from `specimen/benchmark/`:** that harness scores PyNorma's 6
> internal detection strategies against *auto-generated* ground truth (a heuristic,
> somewhat circular baseline). This testbed instead pins down **trustworthy ground
> truth** and measures the **public `Pipeline` API end-to-end** — detection → cleaning —
> so a score means "how close is the library a user actually calls to the right answer."

## What's inside

| Path | Tracked? | What it is |
|------|----------|------------|
| `manifest.json` | ✅ committed | The reference: per-file ground truth (table regions, cleaned shape, messiness tags) + pinned `sha256`/dims. |
| `fetch.py` | ✅ committed | Reproducibly (re)builds the raw data pool: downloads the real datasets (commit-pinned, sanitized) and regenerates the synthetic specimens. |
| `runner.py` | ✅ committed | Runs `pynorma.Pipeline` over every file and scores it against `manifest.json`. |
| `CATALOG.md` | ✅ committed | Human-readable catalog of all files, difficulty, tags, sources & licenses. |
| `results/scorecard.md` | ✅ committed | Snapshot of the latest run (regenerable). |
| `data/` | 🚫 gitignored | The raw CSV/XLSX. **Never committed** — rebuild locally with `fetch.py`. |

**Why data isn't committed:** only the *source* of the corpus lives in the repo — the
download URLs and build logic (`fetch.py`) plus the labels (`manifest.json`). This keeps
the repo small and license-clean while remaining fully reproducible. See the project
`.gitignore` (`/testbed/data/`), which mirrors the existing `/specimen/` convention.

## Corpus

**55 files = 22 synthetic adversarial + 33 real-world.**

- **Synthetic (22):** deterministic (`seed=42`) specimens, each isolating one hazard —
  multi-header, merged cells, side-by-side tables, interspersed subtotals, extreme
  sparsity/raggedness, pivot/crosstab, no-header, single-column, encoding chaos, etc.
  Ground truth is derived from the generators and verified against the actual grids.
- **Real-world (33):** downloaded from public sources and hand-labeled by grid
  inspection. Includes the canonical "untidy data" set (Wickham/`tidyr`: billboard,
  WHO TB, `relig_income`, `weather`, `table4a`), US government statistical XLSX
  (Census H-1, BLS CPS, NCES, NEA — real title rows / multi-level headers / merged
  cells / footnotes), classic ML sets with real missingness (UCI Adult, Titanic,
  Penguins), 1NF/multi-valued-cell sets (MovieLens genres, Netflix cast/genre lists,
  goodbooks authors), a TSV (`chipotle`), and the previously-collected messy
  real-world set (OxfordIHTM, eyowhite, …).

See **[CATALOG.md](CATALOG.md)** for the full list with sources and licenses.

## Latest snapshot

`pynorma.Pipeline` (auto-select) vs ground truth — see **[results/scorecard.md](results/scorecard.md)**:

| Metric | Value |
|--------|-------|
| Pass rate | **50 / 55 (91%)** |
| Mean region IoU | **0.922** |
| Mean header accuracy | **0.901** |
| Table-count match | **53 / 55** |

The 5 non-passing files are known-hard detection challenges, each a useful signal:
`05_merged_cells_mess` & `10_multiple_tables_one_sheet` (drops a merged left column / doesn't
split side-by-side tables), `census_h1_income_limits` (4 stacked sub-tables read as one),
`tidy_billboard_wide` (trims trailing all-empty week columns), and `06_pivot_style_table`
(region extends over trailing subtotals — the *cleaned* table is nonetheless correct).

## Quickstart

```bash
# 1. Build the data pool (downloads real files + regenerates synthetic ones)
python testbed/fetch.py

# 2. Run the benchmark against the shipping Pipeline (auto strategy)
python testbed/runner.py

#    → writes testbed/results/scorecard.md  (+ scorecard.raw.json, gitignored)
```

Useful flags:

```bash
python testbed/fetch.py --skip-specimens   # reuse already-collected specimen/ files
python testbed/runner.py --strategy D      # force a single detection strategy (A–F)
python testbed/runner.py --only titanic,tidy_billboard_wide   # a subset
```

## Ground-truth convention

Every table is described by five 0-indexed integers (the same abstraction PyNorma uses):

```
header : row index of the column-name row   (-1 if the table has no header)
top    : first DATA row      (inclusive)
left   : first DATA column   (inclusive)
bottom : last  DATA row      (inclusive — excludes trailing total/footnote/blank rows)
right  : last  DATA column   (EXCLUSIVE)
```

Interior subtotal rows and interior empty columns stay *inside* the region — only the
outer frame of noise (titles, unit rows, legends, footnotes, blank margins) is trimmed.
Multi-table sheets carry one region per table; `primary` describes the first (top-left) one.

## Scoring

For each file the runner runs `Pipeline(path).detect().clean()` and compares to ground truth:

- **region IoU** — cell-overlap between predicted and ground-truth table regions (greedy best-match).
- **header accuracy** — `1 / (1 + |Δheader-row|)`, averaged over matched tables.
- **table-count match** — did it find the right number of tables?
- **column-count match** — does the primary cleaned table have the expected width?
- **1NF recall** — for files with multi-valued columns, does `detect_multivalue_columns` find them?

A file **passes** when: table-count matches **and** region IoU ≥ `0.60` **and** column-count matches.
The scorecard also breaks pass-rate down by difficulty (🟢 easy · 🟡 medium · 🟠 hard · 🔴 adversarial).

## Reproducibility & drift

- GitHub raw URLs are **pinned to a commit SHA**; `manifest.json` records the expected
  `sha256`, byte size and grid dimensions of every file, so upstream drift is detectable.
- Synthetic specimens are deterministic (`seed=42`) → byte-identical on every rebuild.
- A few sources are unavoidably branch-pinned or on institutional hosts (e.g. UCI); if one
  moves, `fetch.py` reports the failure and continues.

> **Note:** ensemble detection lives in `specimen/benchmark/` (which PyNorma imports at
> runtime). It's present in the working tree; on a fresh checkout that excludes `specimen/`,
> `Pipeline` falls back to `pynorma.parse()`. Regenerate it via the `specimen/` collectors
> if needed.
