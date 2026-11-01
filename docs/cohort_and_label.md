# Cohort and Label Definitions

**Purpose:** Defines who is in the study and what "discontinued" means.
**Owner:** Whole team
**Last updated:** 2026-10-28
**Status:** Confirmed by the team

---

## Cohort (who is included)

| Rule | Definition |
|------|------------|
| Age | Age 18 or older at round 1 (`AGE1X >= 18`) |
| Follow-up | Observed through all five rounds (`ALL5RDS = 1`) |
| Exclusions | Exclude people reported as deceased, institutionalized, active-duty military, or moved out of the country (`DIED`, `INST`, `MILITARY`, or `LEFTUS` = 1) |
| Baseline statin use | At least one statin purchase across rounds 1–2 (in either round) |

## Label (the outcome we predict)

| Label | Definition |
|-------|------------|
| Discontinued (1) | **Zero** statin purchases in rounds 3, 4, and 5 |
| Continued (0) | **At least one** statin purchase in rounds 3–5 |

## Rules

- Switching from one statin to another counts as **continued**.
- All model features come only from rounds 1–2, to prevent data leakage.
- Report the number of people remaining and excluded at each cohort step.
- Report both outcome counts and proportions in the eligible cohort.
- MEPS uses numeric status codes; the Panel 27 file represents the exclusion
  flags as 0 (no) and 1 (yes), and `ALL5RDS` as 1 (yes) and 0 (no).
- Statin purchases are flagged using MEPS therapeutic subclass code 173 in
  either subclass field, or a recognized generic/brand statin name. Recognized
  names are standardized to a canonical generic when possible; class-coded
  purchases with an unknown name remain included and are marked as unmapped.
  The proposed brand list still requires team review under KAN-17.
- Round 3 appears in both prescribed-medicines files. Deduplicate repeated
  purchases by person and prescription-record ID. If duplicate copies disagree
  on statin identification, treat the purchase as a statin and report the
  conflict count in `data/interim/linkage_data_quality.csv` so a possible
  continuation is not silently labeled as discontinuation.
- The deduplicated statin purchase extract is written to
  `data/interim/statin_purchases.csv`; the mapping and unresolved-name counts
  are in `data/interim/linkage_data_quality.csv`.

## Known limitations

- The outcome is **no observed purchase** in rounds 3–5, not proof that the
  patient chose to stop taking a statin. MEPS does not establish the reason.
- Purchases are observed by interview round, not exact fill dates or days
  covered, so the outcome is coarser than a claims-based adherence measure.

## Reproducible build

Build the linked history first, then create the cohort:

```powershell
python -m src.build_person_round_history
python src/build_study_cohort.py
```