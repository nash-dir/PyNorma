# PyNorma Testbed — Scorecard

Generated: 2026-07-06T00:21:06+00:00  |  strategy: `auto`  |  pynorma 1.0.0a1

Evaluates the shipping `pynorma.Pipeline` against **human-verified** ground truth (`manifest.json`).

## Summary

- Files evaluated: **55**  (missing: 0, errors: 0)
- **Pass rate: 55/55 (100%)**  — pass = table-count match AND region IoU ≥ 0.60 AND column-count match
- Mean region IoU: **0.984**
- Mean header accuracy: **0.982**
- Table-count match: **55/55**

## Pass rate by difficulty

| Difficulty | Pass | Total | Rate |
|---|---|---|---|
| easy | 9 | 9 | 100% |
| medium | 28 | 28 | 100% |
| hard | 11 | 11 | 100% |
| adversarial | 7 | 7 | 100% |

## Per-file results

| File | Diff | GT×Pred tables | IoU | Hdr | Cols | Shape | 1NF | Pass | ms |
|---|---|---|---|---|---|---|---|---|---|
| `01_messy_sales` | medium | 1×1 | 1.00 | 1.00 | ✓ | 200×8 | — | ✅ | 86 |
| `02_multiheader_report` | hard | 1×1 | 1.00 | 1.00 | ✓ | 8×6 | — | ✅ | 9 |
| `03_encoding_chaos` | medium | 1×1 | 1.00 | 1.00 | ✓ | 11×4 | — | ✅ | 6 |
| `04_ragged_columns` | hard | 1×1 | 0.71 | 1.00 | ✓ | 80×7 | — | ✅ | 13 |
| `05_merged_cells_mess` | hard | 1×1 | 0.91 | 1.00 | ✓ | 6×6 | — | ✅ | 17 |
| `06_pivot_style_table` | medium | 1×1 | 1.00 | 1.00 | ✓ | 4×8 | — | ✅ | 6 |
| `07_semicolon_european` | medium | 1×1 | 1.00 | 1.00 | ✓ | 60×4 | — | ✅ | 14 |
| `08_annotated_stats_table` | hard | 1×1 | 1.00 | 1.00 | ✓ | 10×8 | — | ✅ | 14 |
| `09_wide_sparse` | hard | 1×1 | 1.00 | 1.00 | ✓ | 40×50 | — | ✅ | 29 |
| `10_multiple_tables_one_sheet` | adversarial | 3×3 | 1.00 | 1.00 | ✓ | 5×3 | — | ✅ | 16 |
| `11_no_header_numeric` | medium | 1×1 | 1.00 | 1.00 | ✓ | 100×6 | — | ✅ | 18 |
| `12_deep_multiheader` | adversarial | 1×1 | 1.00 | 1.00 | ✓ | 6×8 | — | ✅ | 9 |
| `13_pivot_crosstab` | medium | 1×1 | 1.00 | 1.00 | ✓ | 8×7 | — | ✅ | 4 |
| `14_three_tables_gapped` | hard | 3×3 | 1.00 | 1.00 | ✓ | 10×4 | — | ✅ | 9 |
| `15_subtotals_interspersed` | hard | 1×1 | 0.88 | 1.00 | ✓ | 12×7 | — | ✅ | 6 |
| `16_extreme_sparse` | adversarial | 1×1 | 1.00 | 1.00 | ✓ | 200×31 | — | ✅ | 50 |
| `17_crosstab_rowheaders` | adversarial | 1×1 | 1.00 | 0.50 | ✓ | 10×7 | — | ✅ | 8 |
| `18_empty_cols_middle` | medium | 1×1 | 1.00 | 1.00 | ✓ | 50×7 | — | ✅ | 14 |
| `19_title_footnotes_heavy` | hard | 1×1 | 1.00 | 1.00 | ✓ | 7×7 | — | ✅ | 9 |
| `20_mixed_lang_units` | medium | 1×1 | 1.00 | 0.50 | ✓ | 80×6 | — | ✅ | 28 |
| `21_extreme_ragged` | adversarial | 1×1 | 1.00 | 1.00 | ✓ | 60×8 | — | ✅ | 14 |
| `22_single_column` | medium | 1×1 | 1.00 | 1.00 | ✓ | 150×1 | — | ✅ | 8 |
| `bls_cps_occupation_by_industry_2015` | hard | 1×1 | 0.99 | 1.00 | ✓ | 119×13 | — | ✅ | 113 |
| `census_h1_income_limits` | hard | 4×4 | 1.00 | 1.00 | ✓ | 20×7 | — | ✅ | 53 |
| `dat8_chipotle_orders` | medium | 1×1 | 1.00 | 1.00 | ✓ | 4563×5 | 1.00 | ✅ | 1073 |
| `diabetes_missing_data` | easy | 1×1 | 1.00 | 1.00 | ✓ | 768×9 | — | ✅ | 178 |
| `github_messy_data` | medium | 1×1 | 1.00 | 1.00 | ✓ | 165×7 | — | ✅ | 42 |
| `global_world_cities` | easy | 1×1 | 1.00 | 1.00 | ✓ | 33247×4 | — | ✅ | 7130 |
| `goodbooks_books` | medium | 1×1 | 1.00 | 1.00 | ✓ | 9939×23 | 1.00 | ✅ | 9446 |
| `movielens_movies` | medium | 1×1 | 1.00 | 1.00 | ✓ | 27123×3 | 1.00 | ✅ | 4975 |
| `nces_educational_attainment_104_10` | medium | 1×1 | 1.00 | 1.00 | ✓ | 41×19 | — | ✅ | 54 |
| `nea_artists_in_workforce_table1a` | hard | 1×1 | 0.65 | 1.00 | ✓ | 25×14 | — | ✅ | 40 |
| `netflix_titles` | medium | 1×1 | 1.00 | 1.00 | ✓ | 7498×12 | 1.00 | ✅ | 7317 |
| `realworld_automobile` | medium | 1×1 | 1.00 | 1.00 | ✓ | 205×26 | — | ✅ | 177 |
| `realworld_cyclones_philippines` | easy | 1×1 | 1.00 | 1.00 | ✓ | 101×9 | — | ✅ | 69 |
| `realworld_datascience_jobs_uncleaned` | medium | 1×1 | 1.00 | 1.00 | ✓ | 436×15 | — | ✅ | 3516 |
| `realworld_healthcare_messy` | medium | 1×1 | 1.00 | 1.00 | ✓ | 1000×10 | — | ✅ | 477 |
| `realworld_hr_messy` | medium | 1×1 | 1.00 | 1.00 | ✓ | 1000×10 | — | ✅ | 492 |
| `realworld_ihtm_survey_2025` | medium | 1×1 | 1.00 | 1.00 | ✓ | 8×9 | — | ✅ | 17 |
| `realworld_imdb_messy` | medium | 1×1 | 1.00 | 1.00 | ✓ | 99×12 | 1.00 | ✅ | 64 |
| `realworld_occupational_health` | adversarial | 4×4 | 1.00 | 1.00 | ✓ | 14×13 | — | ✅ | 3950 |
| `realworld_population_deaths` | medium | 1×1 | 1.00 | 1.00 | ✓ | 86×23 | — | ✅ | 72 |
| `realworld_vaccine_study` | adversarial | 1×1 | 1.00 | 1.00 | ✓ | 294×28 | — | ✅ | 968 |
| `realworld_warehouse_messy` | medium | 1×1 | 1.00 | 1.00 | ✓ | 1000×10 | — | ✅ | 518 |
| `seaborn_penguins` | easy | 1×1 | 1.00 | 1.00 | ✓ | 344×7 | — | ✅ | 106 |
| `seaborn_titanic` | easy | 1×1 | 1.00 | 1.00 | ✓ | 784×15 | — | ✅ | 517 |
| `tidy_billboard_wide` | medium | 1×1 | 1.00 | 1.00 | ✓ | 316×83 | — | ✅ | 362 |
| `tidy_relig_income_pew` | easy | 1×1 | 1.00 | 1.00 | ✓ | 18×11 | — | ✅ | 11 |
| `tidy_table4a_pivot` | easy | 1×1 | 1.00 | 1.00 | ✓ | 3×3 | — | ✅ | 3 |
| `tidy_us_rent_income` | easy | 1×1 | 1.00 | 1.00 | ✓ | 104×5 | — | ✅ | 26 |
| `tidy_weather_wide` | medium | 1×1 | 1.00 | 1.00 | ✓ | 22×35 | — | ✅ | 18 |
| `tidyr_who_tb` | medium | 1×1 | 1.00 | 1.00 | ✓ | 7240×60 | — | ✅ | 5352 |
| `tidytuesday_coffee_ratings` | medium | 1×1 | 1.00 | 1.00 | ✓ | 1330×43 | — | ✅ | 2471 |
| `tidytuesday_us_avg_tuition` | easy | 1×1 | 1.00 | 1.00 | ✓ | 50×13 | — | ✅ | 112 |
| `uci_adult_census` | medium | 1×1 | 1.00 | 1.00 | ✓ | 32537×15 | — | ✅ | 22228 |
