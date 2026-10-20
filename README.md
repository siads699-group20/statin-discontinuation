# Predicting Statin Discontinuation Risk

An early-warning system that predicts which statin users are at risk of stopping
their medication, explains why, and drafts a suggested next action for a
pharmacist or care manager to review.

> ⚠️ Prototype for a University of Michigan capstone (SIADS 699).
> Not for clinical or coverage decisions.

## How it works

1. **Predict:** a model scores each patient's risk of stopping statins.
2. **Explain:** SHAP shows the main drivers of that risk (for example, high out-of-pocket cost).
3. **Retrieve:** a RAG pipeline finds relevant guidance from public clinical documents.
4. **Draft:** an agent suggests a next action, with citations.
5. **Review:** a person approves, edits, or rejects it in the Streamlit app.

## Data

We use public MEPS (Medical Expenditure Panel Survey) data from AHRQ.
The data is not stored in this repo.
See [docs/meps_sources.md](docs/meps_sources.md) for the file list and links.

## Getting started

1. Clone the repo
2. Install packages: `pip install -r requirements.txt`
3. Download the data: `python scripts/download_meps.py`
4. Run the notebooks in order, starting with `notebooks/01_run_pipeline.ipynb`

## Repo structure

- `docs/` – project documentation
- `scripts/` – data download script
- `notebooks/` – analysis, modeling, RAG, and agent work
- `app/` – Streamlit app
- `outputs/` – results and charts

## Results

Coming soon.

## Team

SIADS 699 Group 20: Maria Febus, [Teammate 2], [Teammate 3], [Teammate 4]

## Use of AI tools

See [docs/ai_use.md](docs/ai_use.md).

## License

[To be decided by the team]
