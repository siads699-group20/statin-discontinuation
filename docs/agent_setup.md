# Agent Setup

**Purpose:** How to install and run the Claude Code subagents the team uses as development helpers.
**Owner:** TBD
**Last updated:** YYYY-MM-DD

> Full setup instructions live in the team Google Drive ("Running the MEPS Data-Prep Agent"). TODO: paste or link.

---

## Agents

| Agent | Job | Can edit files? |
|-------|-----|-----------------|
| meps-data-prep | Downloads and prepares MEPS data | Yes (not raw data) |
| code-reviewer | Reviews code, focused on data leakage | No (read-only) |

## Rules for meps-data-prep

- Plans before acting.
- Never modifies files in `data/raw/`.
- Never defines cohort or label logic (team decisions).
- Writes a plain-English explanation for every script.

## Where agent files live

`.claude/agents/`

## How to run

1. TODO
2. TODO
