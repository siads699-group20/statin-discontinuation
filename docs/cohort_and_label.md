# Cohort and Label Definitions

**Purpose:** Defines who is in the study and what "discontinued" means. These are team decisions; the data-prep agent does not change them.
**Owner:** Whole team
**Last updated:** YYYY-MM-DD
**Status:** Draft – confirm with team

---

## Data source

- **Primary:** MEPS Panel 27 (2022–2023)
- **Fallback:** Panel 26

## Cohort (who is included)

| Rule | Definition |
|------|------------|
| Age | Adults 18 and older |
| Follow-up | Has data in all 5 rounds |
| Established statin user | At least one statin purchase in **both** round 1 and round 2 |

## Label (the outcome we predict)

| Label | Definition |
|-------|------------|
| Discontinued (1) | **Zero** statin purchases in rounds 3, 4, and 5 |
| Continued (0) | **At least one** statin purchase in rounds 3–5 |

## Rules

- Switching from one statin to another counts as **continued**.
- All model features come only from rounds 1–2, to prevent data leakage.

## Known limitations

- People who leave the survey (attrition) are excluded, which may make the cohort healthier than the general population.
- We can't tell if a patient chose to stop or a doctor stopped the drug.
