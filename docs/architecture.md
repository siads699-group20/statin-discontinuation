# System Architecture

**Purpose:** Shows how the model, RAG pipeline, agent, and app connect, and what passes between them.
**Owner:** TBD
**Last updated:** YYYY-MM-DD

---

## Overview

```mermaid
flowchart LR
    A[MEPS raw files] --> B[Data pipeline]
    B --> C[Risk model]
    C --> D[SHAP explanations]
    D --> F[Next-action agent]
    E[RAG corpus] --> G[Retriever]
    G --> F
    F --> H[Streamlit app]
    H --> I[Human review]
```

## Handoffs

| From | To | What passes | Format |
|------|----|-------------|--------|
| Data pipeline | Model | Analysis-ready dataset | Parquet |
| SHAP | Agent | Patient risk score and top drivers | JSON |
| Retriever | Agent | Relevant passages with sources | Python `retrieve()` function |
| Agent | App | Drafted next action with citations | TODO |

## Key rule

Nothing happens automatically. A person approves, edits, or rejects every suggestion.
