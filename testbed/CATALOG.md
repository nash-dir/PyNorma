# PyNorma Testbed — Catalog

> Auto-generated from `manifest.json`. Raw data files are **not** committed (see `.gitignore`); rebuild them with `python testbed/fetch.py`.

**55 reference files** — 22 synthetic adversarial + 33 real-world — all with human-verified ground truth (55/55 labeled).

**Difficulty:** 🟢 easy ×9  🟡 medium ×28  🟠 hard ×11  🔴 adversarial ×7

**Most common challenges:** `missing_markers`×35, `mixed_types`×19, `footnotes`×12, `blank_rows`×12, `wide`×12, `title_rows`×11, `subtotals`×9, `multi_header`×8, `pivot_crosstab`×8, `multilingual`×7, `unit_row`×6, `sparse`×6, `row_headers`×6, `merged_cells`×5, `one_nf_violation`×5, `multivalue_cells`×5, `multi_table`×4, `leading_blank_cols`×3


## Synthetic adversarial specimens (22)

Deterministically generated (seed=42) to isolate specific detection hazards. Ground truth derived from the generators and verified against the actual grids.

| # | File | Fmt | Grid | Ground truth | Diff | Tags |
|---|------|-----|------|--------------|------|------|
| 1 | `01_messy_sales` | csv | 226×8 | 1 tbl · hdr=0 [1:223]×[0:8) | 🟡 | missing_markers, mixed_types, subtotals, footnotes, duplicate_rows |
| 2 | `03_encoding_chaos` | csv | 13×4 | 1 tbl · hdr=0 [1:12]×[0:4) | 🟡 | multilingual, mixed_types, missing_markers, embedded_newlines, formula_injection |
| 3 | `06_pivot_style_table` | csv | 11×8 | 1 tbl · hdr=0 [1:4]×[0:8) | 🟡 | pivot_crosstab, wide, subtotals, footnotes, blank_rows |
| 4 | `07_semicolon_european` | csv | 61×4 | 1 tbl · hdr=0 [1:60]×[0:4) | 🟡 | semicolon, european_decimal, missing_markers, multilingual |
| 5 | `11_no_header_numeric` | csv | 100×6 | 1 tbl · hdr=-1 [0:99]×[0:6) | 🟡 | no_header |
| 6 | `13_pivot_crosstab` | csv | 10×7 | 1 tbl · hdr=0 [1:8]×[0:7) | 🟡 | pivot_crosstab, subtotals, multilingual |
| 7 | `18_empty_cols_middle` | csv | 51×7 | 1 tbl · hdr=0 [1:50]×[0:7) | 🟡 | empty_cols, missing_markers |
| 8 | `20_mixed_lang_units` | csv | 82×6 | 1 tbl · hdr=0 [2:81]×[0:6) | 🟡 | unit_row, multilingual, multi_header, mixed_types |
| 9 | `22_single_column` | csv | 151×1 | 1 tbl · hdr=0 [1:150]×[0:1) | 🟡 | single_column, no_multivalue |
| 10 | `02_multiheader_report` | csv | 17×6 | 1 tbl · hdr=3 [5:12]×[0:6) | 🟠 | title_rows, unit_row, multi_header, subtotals, footnotes |
| 11 | `04_ragged_columns` | csv | 81×7 | 1 tbl · hdr=0 [1:80]×[0:5) | 🟠 | ragged, missing_markers |
| 12 | `05_merged_cells_mess` | xlsx | 18×6 | 1 tbl · hdr=3 [4:14]×[0:6) | 🟠 | title_rows, merged_cells, subtotals, footnotes, blank_rows |
| 13 | `08_annotated_stats_table` | xlsx | 18×8 | 1 tbl · hdr=3 [4:13]×[0:8) | 🟠 | title_rows, unit_row, footnotes, side_annotation, missing_markers |
| 14 | `09_wide_sparse` | csv | 41×50 | 1 tbl · hdr=0 [1:40]×[0:50) | 🟠 | wide, sparse, giant_wide |
| 15 | `14_three_tables_gapped` | csv | 37×5 | 3 tbl · hdr=0 [1:10]×[0:4) | 🟠 | multi_table, blank_rows, footnotes |
| 16 | `15_subtotals_interspersed` | csv | 19×7 | 1 tbl · hdr=0 [1:16]×[0:7) | 🟠 | subtotals, leading_blank_cols, footnotes, unit_row |
| 17 | `19_title_footnotes_heavy` | csv | 19×7 | 1 tbl · hdr=5 [6:12]×[0:7) | 🟠 | title_rows, footnotes, legend_row, multi_header |
| 18 | `10_multiple_tables_one_sheet` | xlsx | 21×7 | 3 tbl · hdr=1 [2:6]×[0:3) | 🔴 | multi_table, side_by_side, title_rows, missing_markers |
| 19 | `12_deep_multiheader` | csv | 18×8 | 1 tbl · hdr=5 [8:13]×[0:8) | 🔴 | title_rows, multi_header, unit_row, subtotals, footnotes |
| 20 | `16_extreme_sparse` | csv | 201×31 | 1 tbl · hdr=0 [1:200]×[0:31) | 🔴 | sparse, wide, giant_wide |
| 21 | `17_crosstab_rowheaders` | csv | 12×7 | 1 tbl · hdr=1 [2:11]×[0:7) | 🔴 | multi_header, pivot_crosstab, row_headers, leading_blank_cols |
| 22 | `21_extreme_ragged` | csv | 61×8 | 1 tbl · hdr=0 [1:60]×[0:8) | 🔴 | ragged |

## Real-world references (33)

Downloaded from public sources (commit-pinned where possible), sanitized on fetch. Ground truth hand-labeled by grid inspection.

| # | File | Fmt | Grid | Ground truth | Diff | Tags |
|---|------|-----|------|--------------|------|------|
| 1 | `diabetes_missing_data` | csv | 769×9 | 1 tbl · hdr=0 [1:768]×[0:9) | 🟢 | missing_markers |
| 2 | `global_world_cities` | csv | 33357×4 | 1 tbl · hdr=0 [1:33356]×[0:4) | 🟢 | multilingual |
| 3 | `realworld_cyclones_philippines` | xlsx | 102×9 | 1 tbl · hdr=0 [1:101]×[0:9) | 🟢 | missing_markers |
| 4 | `seaborn_penguins` | csv | 345×7 | 1 tbl · hdr=0 [1:344]×[0:7) | 🟢 | missing_markers |
| 5 | `seaborn_titanic` | csv | 892×15 | 1 tbl · hdr=0 [1:891]×[0:15) | 🟢 | missing_markers, mixed_types |
| 6 | `tidy_relig_income_pew` | csv | 19×11 | 1 tbl · hdr=0 [1:18]×[0:11) | 🟢 | pivot_crosstab, row_headers |
| 7 | `tidy_table4a_pivot` | csv | 4×3 | 1 tbl · hdr=0 [1:3]×[0:3) | 🟢 | pivot_crosstab, row_headers |
| 8 | `tidy_us_rent_income` | csv | 105×5 | 1 tbl · hdr=0 [1:104]×[0:5) | 🟢 | missing_markers, mixed_types |
| 9 | `tidytuesday_us_avg_tuition` | xlsx | 51×13 | 1 tbl · hdr=0 [1:50]×[0:13) | 🟢 |  |
| 10 | `dat8_chipotle_orders` | tsv | 4623×5 | 1 tbl · hdr=0 [1:4622]×[0:5) | 🟡 | tsv, missing_markers, mixed_types, one_nf_violation, multivalue_cells |
| 11 | `github_messy_data` | csv | 166×7 | 1 tbl · hdr=0 [1:165]×[0:7) | 🟡 | missing_markers, mixed_types |
| 12 | `goodbooks_books` | csv | 10001×23 | 1 tbl · hdr=0 [1:10000]×[0:23) | 🟡 | wide, multivalue_cells, one_nf_violation, missing_markers, mixed_types |
| 13 | `movielens_movies` | csv | 27279×3 | 1 tbl · hdr=0 [1:27278]×[0:3) | 🟡 | multivalue_cells, one_nf_violation, missing_markers |
| 14 | `nces_educational_attainment_104_10` | xlsx | 49×19 | 1 tbl · hdr=0 [1:48]×[0:19) | 🟡 | blank_rows, missing_markers, mixed_types, wide |
| 15 | `netflix_titles` | csv | 7788×12 | 1 tbl · hdr=0 [1:7787]×[0:12) | 🟡 | missing_markers, one_nf_violation, multivalue_cells, multilingual |
| 16 | `realworld_automobile` | csv | 206×26 | 1 tbl · hdr=0 [1:205]×[0:26) | 🟡 | missing_markers, wide, mixed_types |
| 17 | `realworld_datascience_jobs_uncleaned` | csv | 673×15 | 1 tbl · hdr=0 [1:672]×[0:15) | 🟡 | missing_markers, mixed_types, wide |
| 18 | `realworld_healthcare_messy` | csv | 1001×10 | 1 tbl · hdr=0 [1:1000]×[0:10) | 🟡 | missing_markers, mixed_types, duplicate_rows |
| 19 | `realworld_hr_messy` | csv | 1001×10 | 1 tbl · hdr=0 [1:1000]×[0:10) | 🟡 | missing_markers, mixed_types |
| 20 | `realworld_ihtm_survey_2025` | xlsx | 19×9 | 1 tbl · hdr=0 [1:8]×[0:9) | 🟡 | missing_markers, mixed_types, blank_rows, sparse |
| 21 | `realworld_imdb_messy` | csv | 102×12 | 1 tbl · hdr=0 [1:101]×[0:12) | 🟡 | semicolon, empty_cols, blank_rows, missing_markers, mixed_types |
| 22 | `realworld_population_deaths` | xlsx | 88×23 | 1 tbl · hdr=1 [2:87]×[0:23) | 🟡 | title_rows, wide, merged_cells, missing_markers |
| 23 | `realworld_warehouse_messy` | csv | 1001×10 | 1 tbl · hdr=0 [1:1000]×[0:10) | 🟡 | missing_markers, mixed_types |
| 24 | `tidy_billboard_wide` | csv | 318×83 | 1 tbl · hdr=0 [1:317]×[0:83) | 🟡 | wide, missing_markers |
| 25 | `tidy_weather_wide` | csv | 23×35 | 1 tbl · hdr=0 [1:22]×[0:35) | 🟡 | wide, sparse, missing_markers, pivot_crosstab |
| 26 | `tidyr_who_tb` | csv | 7241×60 | 1 tbl · hdr=0 [1:7240]×[0:60) | 🟡 | wide, sparse, missing_markers |
| 27 | `tidytuesday_coffee_ratings` | csv | 1340×43 | 1 tbl · hdr=0 [1:1339]×[0:43) | 🟡 | missing_markers, mixed_types, wide |
| 28 | `uci_adult_census` | csv | 32562×15 | 1 tbl · hdr=-1 [0:32560]×[0:15) | 🟡 | no_header, missing_markers, mixed_types |
| 29 | `bls_cps_occupation_by_industry_2015` | xlsx | 134×13 | 1 tbl · hdr=5 [7:131]×[0:13) | 🟠 | title_rows, unit_row, multi_header, merged_cells, row_headers |
| 30 | `census_h1_income_limits` | xlsx | 99×7 | 4 tbl · hdr=6 [7:26]×[0:7) | 🟠 | title_rows, multi_header, multi_table, merged_cells, row_headers |
| 31 | `nea_artists_in_workforce_table1a` | xlsx | 43×14 | 1 tbl · hdr=2 [3:28]×[0:14) | 🟠 | title_rows, blank_rows, row_headers, pivot_crosstab, footnotes |
| 32 | `realworld_occupational_health` | xlsx | 1048576×14 | 4 tbl · hdr=5 [6:19]×[1:14) | 🔴 | title_rows, multi_header, multi_table, pivot_crosstab, subtotals |
| 33 | `realworld_vaccine_study` | xlsx | 301×1024 | 1 tbl · hdr=0 [1:294]×[0:28) | 🔴 | ghost_dimension, empty_cols, blank_rows, missing_markers, mixed_types |

## Sources & licenses

| File | Provider | License | URL |
|------|----------|---------|-----|
| `bls_cps_occupation_by_industry_2015` | U.S. Bureau of Labor Statistics, CPS annual averages table cpsaat17 (employed persons by occupation, industry, sex, race), via rfordatascience/tidytuesday (2021-02-23) | US Government public domain (U.S. Bureau of Labor Statistics work); mirror repo rfordatascience/tidytuesday | https://raw.githubusercontent.com/rfordatascience/tidytuesday/428166c724b884f0a9afcc87c… |
| `census_h1_income_limits` | U.S. Census Bureau, Historical Income Tables: Households, Table H-1 (Asian alone-or-in-combination), redistributed via rfordatascience/tidytuesday (2021-02-09) | US Government public domain (U.S. Census Bureau work); mirror repo rfordatascience/tidytuesday | https://raw.githubusercontent.com/rfordatascience/tidytuesday/714c6d44b6c56715eb8f94f82… |
| `dat8_chipotle_orders` | justmarkham/DAT8 (General Assembly Data Science teaching repo); data originally from the TidyText/Chipotle order dataset | unknown (public teaching repo, no explicit LICENSE file) | https://raw.githubusercontent.com/justmarkham/DAT8/7dda003ffa795664e603868d6077e00974d6… |
| `diabetes_missing_data` | YBI-Foundation/Dataset | see YBI-Foundation/Dataset repo | https://github.com/YBI-Foundation/Dataset (Diabetes Missing Data.csv) |
| `github_messy_data` | ryanleeallred/datasets | unknown | https://github.com/ryanleeallred/datasets (messy-data.csv) |
| `global_world_cities` | datasets/world-cities (Core Datasets) | ODC-PDDL / see repo | https://github.com/datasets/world-cities (data/world-cities.csv) |
| `goodbooks_books` | goodbooks-10k (zygmuntz/goodbooks-10k) | See goodbooks-10k repository LICENSE (permissive, MIT-style) | https://raw.githubusercontent.com/zygmuntz/goodbooks-10k/fdb21c94e9e6e3340966a231c5bda9… |
| `movielens_movies` | GroupLens MovieLens (ml-latest) via github mirror nchah/movielens-recommender | MovieLens/GroupLens research-use terms (original data); mirror repo carries no separate LICENSE | https://raw.githubusercontent.com/nchah/movielens-recommender/4c1a69e092bca937f8ef029f4… |
| `nces_educational_attainment_104_10` | U.S. National Center for Education Statistics (NCES), Digest of Education Statistics table 104.10 (educational attainment by race/ethnicity and sex), via rfordatascience/tidytuesday (2021-02-02) | US Government public domain (NCES / U.S. Dept. of Education work); mirror repo rfordatascience/tidytuesday | https://raw.githubusercontent.com/rfordatascience/tidytuesday/184779aada0363db28cdeff6c… |
| `nea_artists_in_workforce_table1a` | U.S. National Endowment for the Arts, 'Artists in the Workforce' National Tables, Table 1a Artist Profile, via rfordatascience/tidytuesday (2022-09-27) | US Government public domain (National Endowment for the Arts work); mirror repo rfordatascience/tidytuesday | https://raw.githubusercontent.com/rfordatascience/tidytuesday/f55f1f30735a689efa3de1877… |
| `netflix_titles` | Netflix Movies and TV Shows (Kaggle, Shivam Bansal) redistributed via rfordatascience/tidytuesday 2021-04-20 | CC0 1.0 (Kaggle source); TidyTuesday redistributes as-is | https://raw.githubusercontent.com/rfordatascience/tidytuesday/f55f1f30735a689efa3de1877… |
| `realworld_automobile` | eyowhite/Messy-dataset | see eyowhite/Messy-dataset repo | https://github.com/eyowhite/Messy-dataset (automobile_dataset.csv) |
| `realworld_cyclones_philippines` | OxfordIHTM/messy-data | see OxfordIHTM/messy-data repo | https://github.com/OxfordIHTM/messy-data (data/cyclones.xlsx) |
| `realworld_datascience_jobs_uncleaned` | eyowhite/Messy-dataset | see eyowhite/Messy-dataset repo | https://github.com/eyowhite/Messy-dataset (Uncleaned_DS_jobs.csv) |
| `realworld_healthcare_messy` | eyowhite/Messy-dataset | see eyowhite/Messy-dataset repo | https://github.com/eyowhite/Messy-dataset (healthcare_messy_data.csv) |
| `realworld_hr_messy` | eyowhite/Messy-dataset | see eyowhite/Messy-dataset repo | https://github.com/eyowhite/Messy-dataset (messy_HR_data.csv) |
| `realworld_ihtm_survey_2025` | OxfordIHTM/messy-data | see OxfordIHTM/messy-data repo | https://github.com/OxfordIHTM/messy-data (data/ihtm_2025.xlsx) |
| `realworld_imdb_messy` | eyowhite/Messy-dataset | see eyowhite/Messy-dataset repo | https://github.com/eyowhite/Messy-dataset (messy_IMDB_dataset.csv) |
| `realworld_occupational_health` | OxfordIHTM/messy-data | see OxfordIHTM/messy-data repo | https://github.com/OxfordIHTM/messy-data (data/occupational_health.xlsx) |
| `realworld_population_deaths` | OxfordIHTM/messy-data | see OxfordIHTM/messy-data repo | https://github.com/OxfordIHTM/messy-data (data/pop_death.xlsx) |
| `realworld_vaccine_study` | OxfordIHTM/messy-data | see OxfordIHTM/messy-data repo | https://github.com/OxfordIHTM/messy-data (data/vaccine.xlsx) |
| `realworld_warehouse_messy` | eyowhite/Messy-dataset | see eyowhite/Messy-dataset repo | https://github.com/eyowhite/Messy-dataset (warehouse_messy_data.csv) |
| `seaborn_penguins` | seaborn-data (mwaskom/seaborn-data GitHub mirror; Palmer Penguins, Gorman/Horst) | CC0 1.0 (Palmer Penguins) | https://raw.githubusercontent.com/mwaskom/seaborn-data/4e06bf0b8c4bf161ed04e9df59b77c35… |
| `seaborn_titanic` | seaborn-data (mwaskom/seaborn-data GitHub mirror) | BSD-3-Clause (seaborn-data mirror) | https://raw.githubusercontent.com/mwaskom/seaborn-data/a29a0141d20e156043ec257a64c8de3b… |
| `tidy_billboard_wide` | hadley/tidy-data data/billboard.csv (Wickham 2014 'Tidy Data' supplement) | Unspecified (research-paper supplement repo; academic use) | https://raw.githubusercontent.com/hadley/tidy-data/25dd834ba47b098d3894481078137b5962c2… |
| `tidy_relig_income_pew` | tidyverse/tidyr data-raw (relig_income); orig. Pew Forum via Wickham 2014, J. Stat. Soft. 59(10) 'Tidy Data' | MIT (tidyverse/tidyr package) | https://raw.githubusercontent.com/tidyverse/tidyr/11572d8c5588e46865efc26b0de6f4b4f0a23… |
| `tidy_table4a_pivot` | tidyverse/tidyr data-raw/table4a.csv (Wickham & Grolemund, R4DS; WHO TB cases) | MIT (tidyverse/tidyr package) | https://raw.githubusercontent.com/tidyverse/tidyr/4fb915d7143c28bcaee6ed7e2b8628c33ba2b… |
| `tidy_us_rent_income` | tidyverse/tidyr data-raw/us_rent_income.csv (US Census ACS via tidyr) | MIT (tidyverse/tidyr package) | https://raw.githubusercontent.com/tidyverse/tidyr/36502c811832319821d40aafed56d58d15491… |
| `tidy_weather_wide` | tidyverse/tidyr vignettes/weather.csv (Wickham 2014 'Tidy Data'; GHCN station MX000017004) | MIT (tidyverse/tidyr package) | https://raw.githubusercontent.com/tidyverse/tidyr/2c35387d4dea6fb5d725ec41b428341a20dcc… |
| `tidyr_who_tb` | tidyverse/tidyr data-raw (World Health Organization Global Tuberculosis Report subset) | MIT (tidyr R package) | https://raw.githubusercontent.com/tidyverse/tidyr/36502c811832319821d40aafed56d58d15491… |
| `tidytuesday_coffee_ratings` | rfordatascience/tidytuesday 2020/2020-07-07 (James LeDoux, Coffee Quality Institute database scrape) | CC0-1.0 (tidytuesday curation); underlying CQI data public | https://raw.githubusercontent.com/rfordatascience/tidytuesday/f2b0b31e316d0e35eef4834b9… |
| `tidytuesday_us_avg_tuition` | rfordatascience/tidytuesday 2018/2018-04-02 (Southern Regional Education Board tuition report, 'Table 5') | CC0-1.0 (tidytuesday curation); underlying SREB report public | https://raw.githubusercontent.com/rfordatascience/tidytuesday/362fa86c328797428736f05c2… |
| `uci_adult_census` | UCI Machine Learning Repository (Adult / Census Income, Becker & Kohavi) | CC BY 4.0 (UCI ML Repository) | https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data |
