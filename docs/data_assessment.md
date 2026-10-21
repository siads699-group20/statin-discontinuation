# Preliminary Data Assessment (Panel 27)

**Purpose:** Findings from first exploring the Panel 27 files, and how we decided to handle them.
**Owner:** TBD
**Last updated:** YYYY-MM-DD

> Full version lives in the team Google Drive. TODO: paste it here or link to it.

---

## Findings

| # | Finding | Impact | Decision |
|---|---------|--------|----------|
| 1 | Missing-value code -15 ("cannot be computed") was not in our original rules | Affects about 61% of records in the medicine start-month field | TODO |
| 2 | Missing codes differ by column; some negative values are real data | A blanket "negative = missing" rule would delete real data | Handle missing codes column by column |
| 3 | ID fields lose leading zeros if read as numbers | Joins between files would fail | Read DUPERSID as text |
| 4 | File naming patterns | TODO | TODO |

## Open questions

- TODO
