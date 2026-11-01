# Data Dictionary

**Purpose:** Lists the variables we use, which file they come from, and what they mean.
**Owner:** TBD
**Last updated:** 2026-10-28

---

## How to read this table

- **Variable:** the column name in the MEPS file
- **File:** which MEPS file it comes from
- **Use:** how we use it (ID, feature, label input, or excluded)

## Variables

| Variable | File | Description | Use | Notes |
|----------|------|-------------|-----|-------|
| DUPERSID | All files | Person identifier | ID / join key | Read as text to keep leading zeros |
| RXNAME | HC-239A, HC-248A | Medication name as reported | Statin identification | Standardize brand and generic names |
| RXDRGNAM | HC-239A, HC-248A | Generic medication name | Statin identification | Preferred source for canonical generic name |
| TC1S1_1, TC2S1_1 | HC-239A, HC-248A | Multum therapeutic subclasses | Statin identification | A value of 173 in either field flags a statin |
| RXRECIDX | HC-239A, HC-248A | Prescription record identifier | Deduplication | Combined with DUPERSID to deduplicate annual-file overlap |
| *(example)* | HC-252 | Age | Feature | TODO |
| *(example)* | HC-252 | Insurance type | Feature | TODO |

## Statin mapping and extracts

The linkage step identifies a prescription as a statin when either therapeutic
subclass field equals 173 or its generic/reported medication name matches a
recognized statin generic or brand. Generic names are standardized to
atorvastatin, rosuvastatin, simvastatin, pravastatin, lovastatin, fluvastatin,
or pitavastatin. Name matching checks `RXDRGNAM` first, then generic names in
`RXNAME`, then recognized brands in `RXNAME`. When the drug class identifies
a statin but the name does not identify an ingredient, the purchase is
retained with a blank standardized name and `CLASS_CODE_ONLY` mapping source;
the code does not guess.

The following brand aliases form the proposed mapping list. The ingredient
in combination products is mapped to that product's statin component.

| Canonical generic | Recognized brands |
|-------------------|-------------------|
| Atorvastatin | Lipitor, Caduet, Liptruzet |
| Rosuvastatin | Crestor, Ezallor Sprinkle, Roszet |
| Simvastatin | Zocor, Vytorin, Simcor |
| Pravastatin | Pravachol |
| Lovastatin | Mevacor, Altoprev, Advicor |
| Fluvastatin | Lescol, Lescol XL |
| Pitavastatin | Livalo, Zypitamag |

In the Panel 27 files, Lipitor and Crestor were the only specific brand names
observed among subclass-173 records; the deduplicated extract has one Lipitor
and 29 Crestor records. Generic names were also present, including
dosage/form variants. Some class-coded records contained only the general
“HMG-COA REDUCTASE INHIBITORS (STATINS)” description. The alias list remains
proposed and still requires the team review specified for KAN-17.

`data/interim/statin_purchases.csv` contains one row per unique person and
prescription record ID, with round, standardized generic name, matching method,
source files, raw names, and subclass codes. `person_round_history.csv`
contains round-level purchase counts and the standardized statin names.
Both outputs are generated locally and remain Git-ignored.

## Missing-value codes

| Code | Meaning | Notes |
|------|---------|-------|
| -15 | Cannot be computed | Found in the medicine start-month field |
| *(add others)* | | Check codebooks; some negative values are real data |
