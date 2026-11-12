from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class DemoDataError(ValueError):
    """Raised when the app's demo files are missing or don't match the handoff."""


PATIENT_COLUMNS = (
    "patient_id",
    "risk",
    "risk_tier",
    "top_driver_1",
    "top_driver_2",
    "top_driver_3",
)
IMPORTANCE_COLUMNS = ("feature", "mean_abs_shap", "rank")
SUBGROUP_COLUMNS = (
    "subgroup",
    "group",
    "n",
    "auroc",
    "brier",
    "calibration_gap",
    "high_risk_share",
)
DEMO_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "demo"


@dataclass(frozen=True)
class DemoData:
    patients: list[dict[str, str]]
    global_importance: list[dict[str, str]]
    subgroup_metrics: list[dict[str, str]]
    drafts_questions: Any


def _read_csv(path: Path, required_columns: tuple[str, ...]) -> list[dict[str, str]]:
    if not path.is_file():
        raise DemoDataError(f"Required demo file is missing: {path.name}")

    try:
        with path.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            columns = reader.fieldnames
            if columns is None:
                raise DemoDataError(f"{path.name} is empty or has no header row.")
            missing = [column for column in required_columns if column not in columns]
            if missing:
                raise DemoDataError(
                    f"{path.name} is missing required columns: {', '.join(missing)}"
                )
            rows = list(reader)
    except (OSError, csv.Error, UnicodeError) as error:
        raise DemoDataError(f"Could not read {path.name}: {error}") from error

    if not rows:
        raise DemoDataError(f"{path.name} has a header but no data rows.")
    return rows


def load_demo_data(data_dir: Path = DEMO_DATA_DIR) -> DemoData:
    """Load and validate the app's four agreed demo handoff files."""
    patients = _read_csv(data_dir / "patient_drivers.csv", PATIENT_COLUMNS)
    global_importance = _read_csv(
        data_dir / "global_importance.csv", IMPORTANCE_COLUMNS
    )
    subgroup_metrics = _read_csv(
        data_dir / "subgroup_metrics.csv", SUBGROUP_COLUMNS
    )

    patient_ids = [row["patient_id"] for row in patients]
    invalid_ids = [
        patient_id
        for patient_id in patient_ids
        if not re.fullmatch(r"P\d{4}", patient_id)
    ]
    if invalid_ids:
        raise DemoDataError(
            "patient_drivers.csv must use auto-generated IDs such as P0001; "
            f"invalid ID(s): {', '.join(invalid_ids)}"
        )
    if len(patient_ids) != len(set(patient_ids)):
        raise DemoDataError("patient_drivers.csv contains duplicate patient IDs.")

    overall_rows = [
        row
        for row in subgroup_metrics
        if row["subgroup"] == "overall" and row["group"] == "all"
    ]
    if len(overall_rows) != 1:
        raise DemoDataError(
            "subgroup_metrics.csv must contain exactly one overall/all row."
        )

    questions_path = data_dir / "drafts_questions.json"
    if not questions_path.is_file():
        raise DemoDataError("Required demo file is missing: drafts_questions.json")
    try:
        with questions_path.open(encoding="utf-8") as file:
            drafts_questions = json.load(file)
    except (OSError, json.JSONDecodeError, UnicodeError) as error:
        raise DemoDataError(
            f"Could not read drafts_questions.json: {error}"
        ) from error
    if not isinstance(drafts_questions, (dict, list)):
        raise DemoDataError(
            "drafts_questions.json must contain a patient mapping or a list of drafts."
        )

    return DemoData(
        patients=patients,
        global_importance=global_importance,
        subgroup_metrics=subgroup_metrics,
        drafts_questions=drafts_questions,
    )


def questions_for_patient(
    drafts: Any, patient_id: str
) -> list[dict[str, Any]]:
    """Get one patient's question-only draft from a mapping or patient list."""
    patient_draft: Any = None
    if isinstance(drafts, dict):
        if "patients" in drafts:
            patients = drafts["patients"]
            if not isinstance(patients, list):
                raise DemoDataError(
                    "drafts_questions.json 'patients' must be a list."
                )
            patient_draft = next(
                (
                    item
                    for item in patients
                    if isinstance(item, dict) and item.get("patient_id") == patient_id
                ),
                None,
            )
        else:
            patient_draft = drafts.get(patient_id)
    elif isinstance(drafts, list):
        patient_draft = next(
            (
                item
                for item in drafts
                if isinstance(item, dict) and item.get("patient_id") == patient_id
            ),
            None,
        )

    if patient_draft is None:
        return []
    if isinstance(patient_draft, dict):
        questions = patient_draft.get("questions", [])
    else:
        questions = patient_draft
    if not isinstance(questions, list):
        raise DemoDataError(
            f"Question draft for {patient_id} must contain a list of questions."
        )
    if not all(isinstance(question, dict) for question in questions):
        raise DemoDataError(
            f"Question draft for {patient_id} contains an invalid question."
        )
    return questions
