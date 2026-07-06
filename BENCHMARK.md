# PyNorma — Benchmark Report

A faithful, reproducible account of how PyNorma performs on its evaluation corpora.
All numbers here come from a full local run of the committed code and match the tracked
snapshots ([`testbed/results/scorecard.md`](testbed/results/scorecard.md),
[`specimen/benchmark/eval_results.json`](specimen/benchmark/eval_results.json)).

- **Version:** `pynorma 1.0.0b1`
- **Run environment:** Python 3.12, pandas 3.0, openpyxl 3.1, chardet — Windows
- **Strategy:** `auto` (ensemble of 6 strategies + ground-truth-free `quality_score`)

Absolute timings depend on the machine and are not part of any pass/fail criterion.

---

## 1. Summary

| Harness | What it measures | Headline result |
|---|---|---|
| **Testbed** | Public `Pipeline` detection vs **human-verified** ground truth | **55 / 55 pass (100%)**, region IoU **0.984**, header acc. **0.982** |
| **Long-form eval** | Cell-level fidelity of `→ long` conversion vs hand-labeled truth | micro-F1 **0.9998**, **34 / 36** files perfect |
| **Unit / regression** | `pytest` suite (package + structure tests) | **377 passed**, 1 skipped |

The testbed is the metric that matters most: it scores the **exact public API a user
calls** (`Pipeline(path).detect().clean()`) against ground truth that was verified by
human grid inspection — not against an auto-generated (and somewhat circular) baseline.

---

## 2. Testbed — detection vs human-verified ground truth

**Corpus:** 55 files = 22 synthetic single-hazard specimens (deterministic, `seed=42`) +
33 real-world files (hand-labeled by grid inspection). See
[`testbed/CATALOG.md`](testbed/CATALOG.md) for the full list, sources, and licenses.

**Ground-truth convention** (0-indexed, `manifest.json`): each table is
`(header, top, left, bottom, right)` with `right` exclusive and `header = -1` for a
header-less table. Interior subtotal rows and interior empty columns stay *inside* the
region; only the outer frame of noise (titles, unit rows, legends, footnotes, blank
margins) is trimmed.

**Pass rule:** a file passes when **table-count matches** AND **region IoU ≥ 0.60** AND
**column-count matches**.

### Aggregate

| Metric | Value |
|---|---|
| Files evaluated | 55 (missing 0, errors 0) |
| Pass rate | **55 / 55 (100%)** |
| Mean region IoU | **0.984** |
| Mean header accuracy | **0.982** |
| Table-count match | **55 / 55** |

### By difficulty

| Difficulty | Pass / Total | Rate |
|---|---|---|
| 🟢 easy | 9 / 9 | 100% |
| 🟡 medium | 28 / 28 | 100% |
| 🟠 hard | 11 / 11 | 100% |
| 🔴 adversarial | 7 / 7 | 100% |

### Honest notes on the "100%"

- Passing means IoU ≥ 0.60, not IoU = 1.0. Three files pass with a genuinely imperfect
  region: `nea_artists_in_workforce_table1a` (IoU 0.65), `04_ragged_columns` (0.71), and
  `15_subtotals_interspersed` (0.88). They clear the bar but are the softest results.
- Two files report header accuracy 0.50 (`17_crosstab_rowheaders`, `20_mixed_lang_units`)
  — a crosstab / mixed-unit header where the "correct" header row is itself debatable.
- Multi-table detection is exercised: `10_multiple_tables_one_sheet` (3 tables),
  `14_three_tables_gapped` (3), `census_h1_income_limits` (4),
  `realworld_occupational_health` (4) all match table-count and pass.

### Starting point → now

For context, the detection-overhaul branch began at **50 / 55 (91%)**, IoU 0.922, header
0.901, table-count 53 / 55. The current 55 / 55 was reached with **general** structural
rules (multi-row header resolution, XY-cut segmentation, trailing-summary trimming) — no
per-file or filename-specific handling.

---

## 3. Long-form conversion — cell-level F1

**Harness:** [`specimen/benchmark/evaluate.py`](specimen/benchmark/evaluate.py) against 36
hand-labeled specimens in `ground_truth.json`. For each file it detects the table, melts it
to long form, and compares the resulting `(key…, value)` cells to the ground truth.

| Metric | Value |
|---|---|
| Files | 36 |
| Perfectly reconstructed | **34 / 36** |
| Micro precision | 0.9997 |
| Micro recall | 1.0000 |
| **Micro F1** | **0.9998** |
| Macro F1 | 0.9981 |

The two non-perfect files are `04_ragged_columns.csv` (F1 0.969) and
`08_annotated_stats_table.xlsx` (F1 0.961); both keep recall 1.0 but dip slightly on
precision (a few spurious extra cells from a loose detected region). This confirms that
tuning detection did not break the downstream wide → long transform.

---

## 4. Unit & regression tests

```
pytest tests specimen/benchmark/tests -q
→ 377 passed, 1 skipped
```

The suite covers the package (`tests/`) and the detection engine's structure tests
(`specimen/benchmark/tests/`), including a regression **floor** on the long-form micro-F1
so a future detection change can't silently degrade the melt output. The single skip is a
conditional test; warnings are pandas-3 / pytest-9 deprecation notices, not failures.

---

## 5. Where PyNorma still slips (measured)

These are real, measured gaps — not hypotheticals.

### 5.1 1NF (multi-valued column) recall — mean 1.0 (was 0.733)

`detect_multivalue_columns` is scored on the 5 testbed files that actually contain
multi-valued columns:

| File | 1NF recall | Note |
|---|---|---|
| `dat8_chipotle_orders` | 1.0 | ✓ |
| `goodbooks_books` | 1.0 | ✓ (also over-flags URL columns — harmless for recall) |
| `movielens_movies` | 1.0 | ✓ |
| `netflix_titles` | 1.0 | `cast` now caught by the consistent-list signal; `date_added` excluded as a date (was 0.667) |
| `realworld_imdb_messy` | 1.0 | duplicate-column crash fixed; mojibake header `Genr�` detected (was 0.0) |

Detection combines two signals — atom **overlap** (for lists whose values recur, e.g.
genres/countries) and a **consistent-list** heuristic (many short atoms per cell, for
high-cardinality lists like a cast) — and excludes date-like columns. It remains heuristic:
recall is 1.0 on these files, but it can still over-flag unfamiliar shapes (e.g. URL columns)
or miss lists on unseen data. 1NF recall is **not** part of the testbed pass criteria (all 55
pass regardless).

### 5.2 Other known limitations

- **Auto-select size bias.** The ground-truth-free `quality_score` carries coverage/size
  terms that bias selection toward larger regions — a likely suspect if multi-table block
  selection misbehaves on new data.
- **Summary-row trimming is keyword-based.** Trailing-summary trimming matches summary
  keywords as substrings, so legitimate rows containing words like "total" could in theory
  be over-trimmed. Safe on the current 55 files, but a known-fragile heuristic.
- **One worksheet per workbook.** Auto-selects the tabular sheet (or honors `sheet=`), but
  does not yet combine data spread across multiple sheets.
- **Delimiter coverage.** Comma/tab/semicolon/pipe plus `::` and space-aligned fallbacks;
  other exotic / single-space separators may still be missed.
- **Performance.** Large files can take tens of seconds — `uci_adult_census` (~32k rows)
  takes ~20 s in the tracked run, as `segment_blocks` re-scans the grid multiple times.

---

## 6. Reproduce

From a full checkout with the data pool present (`python testbed/fetch.py`, or copy the
benchmark data into `testbed/data/` and `specimen/`):

```bash
pip install -e ".[dev,cli]"

# On non-UTF-8 consoles (e.g. Windows cp949), export PYTHONIOENCODING=utf-8 first.

# 1) Testbed — primary metric (writes testbed/results/scorecard.md)
python testbed/runner.py                       # → 55/55, IoU 0.984, header 0.982

# 2) Long-form cell-level F1
cd specimen && python -m benchmark.evaluate    # → micro-F1 0.9998, 34/36 perfect
cd ..

# 3) Unit / regression suite
python -m pytest tests specimen/benchmark/tests -q   # → 377 passed, 1 skipped
```

Synthetic specimens are byte-identical on rebuild (`seed=42`); real-world files are pinned
by `sha256` / size / dimensions in `manifest.json`, so upstream drift is detectable.
