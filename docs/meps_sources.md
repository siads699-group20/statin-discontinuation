# MEPS Data Sources

**Purpose:** The official list of MEPS files used in this project, with the links `src/download_meps.py` downloads from.
**Owner:** TBD
**Last updated:** 2026-10-20

---

## Files

| File | Description | Year(s) | Download link |
|------|-------------|---------|---------------|
| HC-252 | Longitudinal file, Panel 27 | 2022–2023 | https://meps.ahrq.gov/mepsweb/data_files/pufs/h252/h252dta.zip |
| HC-239A | Prescribed Medicines | 2022 | https://meps.ahrq.gov/mepsweb/data_files/pufs/h239a/h239adta.zip |
| HC-248A | Prescribed Medicines | 2023 | https://meps.ahrq.gov/mepsweb/data_files/pufs/h248a/h248adta.zip |
| HC-241 | Medical Conditions | 2022 | https://meps.ahrq.gov/mepsweb/data_files/pufs/h241/h241dta.zip |
| HC-249 | Medical Conditions | 2023 | https://meps.ahrq.gov/mepsweb/data_files/pufs/h249/h249dta.zip |

## Rules

- These links must match the `SOURCES` list in `src/download_meps.py`. If you change one, change the other.
- Downloaded files are saved to `data/raw/` and are never edited.

## Source

Agency for Healthcare Research and Quality (AHRQ), Medical Expenditure Panel Survey. https://meps.ahrq.gov
