from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
HISTORY_FILE = ROOT / "data" / "interim" / "person_round_history.csv"
OUTPUT_DIR = ROOT / "data" / "processed"
REQUIRED_COLUMNS = (
    "DUPERSID",
    "PANEL",
    "ROUND",
    "AGE",
    "ALL5RDS",
    "DIED",
    "INST",
    "MILITARY",
    "LEFTUS",
    "statin_purchase_count",
)


def build_study_cohort(
    history: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Apply the confirmed cohort rules and label no statin purchase in rounds 3-5."""
    missing = set(REQUIRED_COLUMNS).difference(history.columns)
    if missing:
        raise ValueError(f"Person-round history is missing columns: {sorted(missing)}")
    if history.duplicated(["DUPERSID", "ROUND"]).any():
        raise ValueError("Person-round history has duplicate person/round rows")

    panel = history.loc[history["PANEL"].eq(27)]
    round_one = panel.loc[panel["ROUND"].eq(1)].copy()
    if round_one.empty or round_one["DUPERSID"].duplicated().any():
        raise ValueError("Expected one round-1 row per Panel 27 person")

    eligible = pd.Series(True, index=round_one.index)
    flow = [{
        "step": "Panel 27 longitudinal records",
        "eligible_n": len(round_one),
        "excluded_at_step": 0,
    }]
    steps = (
        ("Age at round 1 is at least 18", round_one["AGE"].ge(18)),
        ("Not reported as deceased", round_one["DIED"].eq(0)),
        ("Not reported as institutionalized", round_one["INST"].eq(0)),
        ("Not reported as active-duty military", round_one["MILITARY"].eq(0)),
        ("Not reported as moved out of the country", round_one["LEFTUS"].eq(0)),
        ("Observed through all five rounds", round_one["ALL5RDS"].eq(1)),
    )
    for step, condition in steps:
        previous_count = int(eligible.sum())
        eligible &= condition.fillna(False)
        current_count = int(eligible.sum())
        flow.append({
            "step": step,
            "eligible_n": current_count,
            "excluded_at_step": previous_count - current_count,
        })

    baseline = panel.loc[panel["ROUND"].isin((1, 2))]
    baseline_counts = baseline.groupby("DUPERSID")["statin_purchase_count"].sum()
    baseline_users = set(baseline_counts[baseline_counts.gt(0)].index)
    previous_count = int(eligible.sum())
    eligible &= round_one["DUPERSID"].isin(baseline_users)
    cohort = round_one.loc[eligible, ["DUPERSID"]].copy()
    flow.append({
        "step": "At least one statin purchase in rounds 1-2",
        "eligible_n": len(cohort),
        "excluded_at_step": previous_count - len(cohort),
    })
    if cohort.empty:
        raise ValueError("No people meet the confirmed study cohort criteria")

    outcome = panel.loc[panel["ROUND"].isin((3, 4, 5))]
    outcome_counts = outcome.groupby("DUPERSID")["statin_purchase_count"].sum()
    outcome_users = set(outcome_counts[outcome_counts.gt(0)].index)
    cohort["discontinued"] = (
        ~cohort["DUPERSID"].isin(outcome_users)
    ).astype("int8")
    cohort = cohort.sort_values("DUPERSID").reset_index(drop=True)

    label_counts = cohort["discontinued"].value_counts()
    label_balance = pd.DataFrame([
        {
            "label": label,
            "outcome": outcome_name,
            "person_count": int(label_counts.get(label, 0)),
            "proportion": float(label_counts.get(label, 0) / len(cohort)),
        }
        for label, outcome_name in (
            (0, "continued"),
            (1, "no observed statin purchase in rounds 3-5"),
        )
    ])
    quality = pd.DataFrame(
        [
            ("Panel 27 longitudinal people", len(round_one)),
            (
                "Baseline statin purchases in rounds 1-2",
                int(baseline["statin_purchase_count"].sum()),
            ),
            (
                "Outcome-window statin purchases in rounds 3-5",
                int(outcome["statin_purchase_count"].sum()),
            ),
        ],
        columns=("metric", "value"),
    )
    return cohort, pd.DataFrame(flow), label_balance, quality


def main() -> int:
    if not HISTORY_FILE.exists():
        raise FileNotFoundError(
            f"Run the person-round linkage first: "
            f"python -m src.build_person_round_history ({HISTORY_FILE})"
        )

    history = pd.read_csv(HISTORY_FILE, dtype={"DUPERSID": "string"})
    cohort, flow, label_balance, quality = build_study_cohort(history)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cohort.to_csv(OUTPUT_DIR / "study_cohort.csv", index=False)
    flow.to_csv(OUTPUT_DIR / "cohort_flow.csv", index=False)
    label_balance.to_csv(OUTPUT_DIR / "label_balance.csv", index=False)
    quality.to_csv(OUTPUT_DIR / "cohort_data_quality.csv", index=False)

    print(f"Study cohort: {len(cohort):,} people")
    print(f"Outputs written to {OUTPUT_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
