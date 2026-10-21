# Data Understanding

**Purpose:** A plain-English guide to MEPS for anyone new to the data.
**Owner:** Maria Febus
**Last updated:** YYYY-MM-DD

> Full version lives in the team Google Drive. TODO: paste it here or link to it.

---

## What is MEPS?

The Medical Expenditure Panel Survey (MEPS), run by AHRQ, is a national survey of health care use, costs, and who pays. It is public, de-identified, and free to download.

## How the survey works

- A **panel** is a group of people followed over time.
- Each panel is interviewed **five times (rounds) over about two years**.
- Two panels are in the field at the same time, overlapping.
- Interviews happen in person at the home.

## Files we use

| File type | What it holds |
|-----------|---------------|
| Longitudinal | One row per person, across both years of the panel |
| Prescribed Medicines | One row per prescription purchase |
| Medical Conditions | One row per reported condition |

## Why this matters for our project

- Purchases are recorded **by round, not by date**, so we can't calculate PDC.
- We define discontinuation at the round level instead (see [Cohort and Label Definitions](cohort_and_label.md)).
