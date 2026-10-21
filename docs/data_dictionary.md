# Data Dictionary

**Purpose:** Lists the variables we use, which file they come from, and what they mean.
**Owner:** TBD
**Last updated:** YYYY-MM-DD

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
| *(therapeutic sub-class field)* | HC-239A, HC-248A | Multum drug sub-class | Statin identification | Statins = sub-class 173 |
| *(example)* | HC-252 | Age | Feature | TODO |
| *(example)* | HC-252 | Insurance type | Feature | TODO |

> TODO: Verify every variable name against the MEPS codebooks before use.

## Missing-value codes

| Code | Meaning | Notes |
|------|---------|-------|
| -15 | Cannot be computed | Found in the medicine start-month field |
| *(add others)* | | Check codebooks; some negative values are real data |
