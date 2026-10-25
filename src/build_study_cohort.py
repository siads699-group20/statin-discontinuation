"""Build the Panel 27 study cohort and discontinuation label."""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
import pyreadstat


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
OUTPUT_DIR = ROOT / "data" / "processed"
LONGITUDINAL_FILE = "h252dta.zip"
PRESCRIPTION_FILES = ("h239adta.zip", "h248adta.zip")
LONGITUDINAL_COLUMNS = (
    "DUPERSID",
    "PANEL",
    "AGE1X",
    "ALL5RDS",
    "DIED",
    "INST",
    "MILITARY",
    "LEFTUS",
)
PRESCRIPTION_COLUMNS = (
    "DUPERSID",
    "PANEL",
    "PURCHRD",
    "RXRECIDX",
    "RXDRGNAM",
    "TC1S1_1",
    "TC2S1_1",
)
STATIN_NAMES = (
    "ATORVASTATIN",
    "ROSUVASTATIN",
    "SIMVASTATIN",
    "PRAVASTATIN",
    "LOVASTATIN",
    "FLUVASTATIN",
    "PITAVASTATIN",
)
PURCHASE_KEY = ("DUPERSID", "RXRECIDX")


def read_meps_file(filename: str, columns: tuple[str, ...]) -> pd.DataFrame:
    """Read selected columns from a Stata file inside a MEPS ZIP archive."""
    archive_path = RAW_DIR / filename
    with zipfile.ZipFile(archive_path) as archive:
        stata_files = [
            member for member in archive.namelist()
            if member.lower().endswith(".dta")
        ]
        if len(stata_files) != 1:
            raise ValueError(
                f"Expected one Stata file in {archive_path}, found {len(stata_files)}"
            )

        with tempfile.TemporaryDirectory(prefix="meps_cohort_") as temp_dir:
            stata_path = Path(temp_dir) / Path(stata_files[0]).name
            with archive.open(stata_files[0]) as source, stata_path.open("wb") as target:
                shutil.copyfileobj(source, target)
            frame, metadata = pyreadstat.read_dta(
                str(stata_path), usecols=list(columns)
            )

    missing_columns = set(columns).difference(metadata.column_names)
    if missing_columns:
        raise ValueError(
            f"{filename} is missing required columns: {sorted(missing_columns)}"
        )
    return frame


def mark_statin_purchases(prescriptions: pd.DataFrame) -> pd.DataFrame:
    """Flag records with a statin class code or generic name."""
    required = set(PRESCRIPTION_COLUMNS)
    missing = required.difference(prescriptions.columns)
    if missing:
        raise ValueError(f"Prescription data is missing columns: {sorted(missing)}")

    marked = prescriptions.copy()
    class_match = marked["TC1S1_1"].eq(173) | marked["TC2S1_1"].eq(173)
    generic_names = marked["RXDRGNAM"].astype("string").str.upper()
    name_match = generic_names.str.contains(
        "|".join(STATIN_NAMES), regex=True, na=False
    )

    marked["is_statin"] = class_match | name_match
    return marked


def deduplicate_purchases(
    prescriptions: pd.DataFrame,
) -> tuple[pd.DataFrame, int, int]:
    """Deduplicate records by person and purchase ID; keep statin flags if either copy has one."""
    if prescriptions[list(PURCHASE_KEY)].isna().any().any():
        raise ValueError("Prescription data contains missing purchase-key values")

    duplicate_mask = prescriptions.duplicated(list(PURCHASE_KEY), keep=False)
    duplicates = prescriptions.loc[duplicate_mask]
    if duplicates.empty:
        return prescriptions.copy(), 0, 0

    duplicate_groups = duplicates.groupby(list(PURCHASE_KEY), dropna=False)
    if duplicate_groups["PURCHRD"].nunique(dropna=False).gt(1).any():
        raise ValueError("Duplicate prescription IDs disagree on purchase round")

    statin_conflicts = int(
        duplicate_groups["is_statin"]
        .nunique(dropna=False)
        .gt(1)
        .sum()
    )
    duplicate_rows_removed = int(
        prescriptions.duplicated(list(PURCHASE_KEY)).sum()
    )
    unique_purchases = prescriptions.groupby(
        list(PURCHASE_KEY), as_index=False, dropna=False
    ).agg(
        PANEL=("PANEL", "first"),
        PURCHRD=("PURCHRD", "first"),
        is_statin=("is_statin", "any"),
    )
    return unique_purchases, duplicate_rows_removed, statin_conflicts


def build_study_cohort(
    longitudinal: pd.DataFrame,
    prescriptions_2022: pd.DataFrame,
    prescriptions_2023: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Apply the agreed eligibility rules and label people with no later purchase."""
    missing_longitudinal = set(LONGITUDINAL_COLUMNS).difference(longitudinal.columns)
    if missing_longitudinal:
        raise ValueError(
            f"Longitudinal data is missing columns: {sorted(missing_longitudinal)}"
        )
    if longitudinal["DUPERSID"].isna().any():
        raise ValueError("Longitudinal data contains missing DUPERSID values")
    if longitudinal["DUPERSID"].duplicated().any():
        raise ValueError("Longitudinal data must contain one row per DUPERSID")

    panel = longitudinal.loc[longitudinal["PANEL"].eq(27)].copy()
    eligible = pd.Series(True, index=panel.index)
    flow = [{
        "step": "Panel 27 longitudinal records",
        "eligible_n": len(panel),
        "excluded_at_step": 0,
    }]
    steps = (
        ("Age at round 1 is at least 18", panel["AGE1X"].ge(18)),
        ("Not reported as deceased", panel["DIED"].eq(0)),
        ("Not reported as institutionalized", panel["INST"].eq(0)),
        ("Not reported as active-duty military", panel["MILITARY"].eq(0)),
        ("Not reported as moved out of the country", panel["LEFTUS"].eq(0)),
        ("Observed through all five rounds", panel["ALL5RDS"].eq(1)),
    )
    for step, condition in steps:
        previous_n = int(eligible.sum())
        eligible &= condition.fillna(False)
        flow.append({
            "step": step,
            "eligible_n": int(eligible.sum()),
            "excluded_at_step": previous_n - int(eligible.sum()),
        })

    pmed22 = mark_statin_purchases(prescriptions_2022)
    pmed23 = mark_statin_purchases(prescriptions_2023)
    pmed22 = pmed22.loc[pmed22["PANEL"].eq(27)].copy()
    pmed23 = pmed23.loc[pmed23["PANEL"].eq(27)].copy()
    baseline = pmed22.loc[pmed22["is_statin"] & pmed22["PURCHRD"].isin((1, 2))]
    baseline_users = set(baseline["DUPERSID"].dropna())
    previous_n = int(eligible.sum())
    eligible &= panel["DUPERSID"].isin(baseline_users)
    cohort = panel.loc[eligible, ["DUPERSID"]].copy()
    flow.append({
        "step": "At least one statin purchase in rounds 1-2",
        "eligible_n": len(cohort),
        "excluded_at_step": previous_n - len(cohort),
    })
    if cohort.empty:
        raise ValueError("No people meet the confirmed study cohort criteria")

    outcome_records = pd.concat([
        pmed22.loc[pmed22["PURCHRD"].isin((3, 4, 5))],
        pmed23.loc[pmed23["PURCHRD"].isin((3, 4, 5))],
    ], ignore_index=True)
    unique_purchases, duplicate_rows_removed, statin_conflicts = (
        deduplicate_purchases(outcome_records)
    )
    outcome_users = set(unique_purchases.loc[
        unique_purchases["is_statin"], "DUPERSID"
    ].dropna())
    cohort["discontinued"] = (~cohort["DUPERSID"].isin(outcome_users)).astype("int8")
    cohort = cohort.sort_values("DUPERSID").reset_index(drop=True)

    counts = cohort["discontinued"].value_counts()
    label_balance = pd.DataFrame([
        {
            "label": label,
            "outcome": outcome,
            "person_count": int(counts.get(label, 0)),
            "proportion": float(counts.get(label, 0) / len(cohort)),
        }
        for label, outcome in (
            (0, "continued"),
            (1, "no observed statin purchase in rounds 3-5"),
        )
    ])
    quality = pd.DataFrame(
        [
            ("Panel 27 longitudinal rows", len(panel)),
            ("Panel 27 baseline statin purchase records, rounds 1-2", len(baseline)),
            (
                "Unique Panel 27 outcome-window statin purchase records",
                int(unique_purchases["is_statin"].sum()),
            ),
            ("Duplicate outcome-window purchase rows removed", duplicate_rows_removed),
            ("Duplicate purchase IDs with conflicting statin flags", statin_conflicts),
        ],
        columns=("metric", "value"),
    )
    return cohort, pd.DataFrame(flow), label_balance, quality


def main() -> int:
    longitudinal = read_meps_file(LONGITUDINAL_FILE, LONGITUDINAL_COLUMNS)
    prescriptions_2022 = read_meps_file(PRESCRIPTION_FILES[0], PRESCRIPTION_COLUMNS)
    prescriptions_2023 = read_meps_file(PRESCRIPTION_FILES[1], PRESCRIPTION_COLUMNS)

    cohort, flow, label_balance, quality = build_study_cohort(
        longitudinal, prescriptions_2022, prescriptions_2023
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cohort.to_csv(OUTPUT_DIR / "study_cohort.csv", index=False)
    flow.to_csv(OUTPUT_DIR / "cohort_flow.csv", index=False)
    label_balance.to_csv(OUTPUT_DIR / "label_balance.csv", index=False)
    quality.to_csv(OUTPUT_DIR / "cohort_data_quality.csv", index=False)

    print(f"Study cohort: {len(cohort):,} people")
    print(label_balance.to_string(index=False))
    print(flow.to_string(index=False))
    print(quality.to_string(index=False))
    print(f"Outputs written to {OUTPUT_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
