from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any

import streamlit as st

from app.data import DemoData, DemoDataError, load_demo_data, questions_for_patient


PROTOTYPE_BANNER = (
    "Prototype - not for clinical or coverage decisions. Questions only, no medical advice."
)
LOG_COLUMNS = (
    "timestamp",
    "patient_id",
    "reviewer",
    "decision",
    "edited_text",
    "reason",
    "questions_asked",
    "barrier_confirmed",
    "patient_notes",
    "prompt_version",
    "source",
)
PAGES = ("Overview", "Subgroups", "Patient view", "Answer form and log")
SUBGROUP_ALIASES = {
    "Age": {"age", "age_group", "age group"},
    "Sex": {"sex"},
    "Race/ethnicity": {"race", "race/ethnicity", "race_ethnicity"},
    "Insurance": {"insurance", "insurance_type", "insurance type"},
}


def _number(row: dict[str, str], column: str) -> float:
    try:
        return float(row[column])
    except (KeyError, ValueError) as error:
        raise DemoDataError(
            f"Expected a numeric value in column '{column}', got "
            f"{row.get(column, '<missing>')!r}."
        ) from error


def _overall_metrics(data: DemoData) -> dict[str, str]:
    return next(
        row
        for row in data.subgroup_metrics
        if row["subgroup"] == "overall" and row["group"] == "all"
    )


def _render_overview(data: DemoData) -> None:
    st.title("Overview")
    overall = _overall_metrics(data)
    high_risk_share = _number(overall, "high_risk_share")

    cohort, auroc, brier, high_risk = st.columns(4)
    cohort.metric("Patients in cohort", overall["n"])
    auroc.metric("AUROC", f"{_number(overall, 'auroc'):.3f}")
    brier.metric("Brier score", f"{_number(overall, 'brier'):.3f}")
    high_risk.metric("High-risk share", f"{high_risk_share:.1%}")
    st.caption(
        f"Calibration gap: {_number(overall, 'calibration_gap'):.3f}. "
        "No Star Rating is reported."
    )

    st.subheader("What drives risk")
    chart_data = [
        {
            "feature": row["feature"],
            "mean_abs_shap": _number(row, "mean_abs_shap"),
        }
        for row in data.global_importance
    ]
    st.bar_chart(chart_data, x="feature", y="mean_abs_shap")


def _render_subgroups(data: DemoData) -> None:
    st.title("Subgroups")
    selected_groups: dict[str, str] = {}
    filters = st.columns(4)
    for column, (label, aliases) in zip(filters, SUBGROUP_ALIASES.items()):
        available = sorted(
            {
                row["group"]
                for row in data.subgroup_metrics
                if row["subgroup"].strip().lower() in aliases
            }
        )
        selected_groups[label] = column.selectbox(
            label, ["All"] + available, key=f"subgroup_{label}"
        )

    active_filters = {
        label: (aliases, selected_groups[label])
        for label, aliases in SUBGROUP_ALIASES.items()
        if selected_groups[label] != "All"
    }
    if active_filters:
        filtered_rows = [
            row
            for row in data.subgroup_metrics
            if any(
                row["subgroup"].strip().lower() in aliases
                and row["group"] == selected_group
                for aliases, selected_group in active_filters.values()
            )
        ]
    else:
        filtered_rows = [
            row for row in data.subgroup_metrics if row["subgroup"] != "overall"
        ]
    if not filtered_rows:
        st.info("No subgroup results match these filters.")
        return

    st.dataframe(filtered_rows, width="stretch", hide_index=True)
    st.subheader("High-risk share by subgroup")
    if len(active_filters) > 1:
        st.caption(
            "Selected dimensions are shown separately; these files do not contain "
            "cross-dimension intersection results."
        )
    high_risk_data = [
        {
            "group": f"{row['subgroup']}: {row['group']} (n={row['n']})",
            "high_risk_share": _number(row, "high_risk_share"),
        }
        for row in filtered_rows
    ]
    st.bar_chart(high_risk_data, x="group", y="high_risk_share")
    st.caption("Sample sizes are shown for each subgroup.")


def _source_details(source: Any) -> None:
    if isinstance(source, dict):
        if source.get("title"):
            st.write(f"Source: {source['title']}")
        if source.get("url"):
            st.write(f"URL: {source['url']}")
    elif source:
        st.write(f"Source: {source}")


def _render_questions(drafts: Any, patient_id: str) -> list[dict[str, Any]]:
    questions = questions_for_patient(drafts, patient_id)
    if not questions:
        st.info("No outreach questions are available for this demo patient.")
        return []

    for question in questions:
        text = (
            question.get("question")
            or question.get("question_text")
            or question.get("text")
        )
        if not text:
            raise DemoDataError(
                f"A question for {patient_id} is missing its question text."
            )
        st.write(text)
        if question.get("driver"):
            st.caption(f"Driver: {question['driver']}")
        _source_details(question.get("source"))
        cites = question.get("cites")
        if cites:
            if isinstance(cites, list):
                for citation in cites:
                    _source_details(citation)
            else:
                _source_details(cites)
    return questions


def _render_patient_view(data: DemoData) -> None:
    st.title("Patient view")
    patient_by_id = {row["patient_id"]: row for row in data.patients}
    patient_id = st.selectbox("Demo patient", list(patient_by_id))
    patient = patient_by_id[patient_id]

    risk, tier = st.columns(2)
    risk.metric("Predicted discontinuation risk", f"{_number(patient, 'risk'):.1%}")
    tier.metric("Risk tier", patient["risk_tier"])

    st.subheader("Top risk drivers")
    drivers = [
        patient[column].strip()
        for column in ("top_driver_1", "top_driver_2", "top_driver_3")
        if patient[column].strip()
    ]
    if drivers:
        for driver in drivers:
            st.write(f"- {driver}")
    else:
        st.info("No drivers meet the reporting threshold for this patient.")

    questions: list[dict[str, Any]] = []
    if patient["risk_tier"].strip().lower() == "low":
        st.info("No outreach questions: low risk.")
    else:
        st.subheader("Cited outreach questions")
        questions = _render_questions(data.drafts_questions, patient_id)
    _render_review_form(patient, questions)


def _render_review_form(patient: dict[str, str], questions: list[dict[str, Any]]) -> None:
    question_options = [
        str(question.get("question_id", ""))
        for question in questions
        if question.get("question_id")
    ]
    with st.form("review_form"):
        reviewer = st.text_input("Reviewer")
        decision = st.radio("Decision", ("approve", "edit", "reject"), horizontal=True)
        questions_asked = st.multiselect(
            "Questions asked", question_options, key="questions_asked"
        )
        edited_text = st.text_area("Edited question text")
        reason = st.text_input("Reason")
        barrier = st.selectbox(
            "Barrier confirmed",
            ("cost", "side effects", "complexity", "doubts about need", "other", "none"),
            index=5,
        )
        patient_notes = st.text_area("Patient notes")
        submitted = st.form_submit_button("Save review")

    if submitted:
        if not reviewer.strip():
            st.error("Enter a reviewer before saving the review.")
            return
        if decision == "edit" and not edited_text.strip():
            st.error("Enter the edited text when the decision is edit.")
            return
        review_log = st.session_state["review_log"]
        review_log.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "patient_id": patient["patient_id"],
                "reviewer": reviewer.strip(),
                "decision": decision,
                "edited_text": edited_text.strip(),
                "reason": reason.strip(),
                "questions_asked": ",".join(questions_asked),
                "barrier_confirmed": barrier,
                "patient_notes": patient_notes.strip(),
                "prompt_version": "demo",
                "source": "simulated",
            }
        )
        st.success("Demo review saved for this session.")


def _render_answer_and_log(data: DemoData) -> None:
    st.title("Answer form and log")
    st.caption("Demo only - simulated responses.")
    patient_by_id = {row["patient_id"]: row for row in data.patients}
    patient_id = st.selectbox(
        "Patient to review", list(patient_by_id), key="review_patient_id"
    )
    patient = patient_by_id[patient_id]

    questions: list[dict[str, Any]] = []
    if patient["risk_tier"].strip().lower() == "low":
        st.info("No outreach questions: low risk.")
    else:
        questions = _render_questions(data.drafts_questions, patient_id)
    _render_review_form(patient, questions)

    st.subheader("Review log")
    review_log: list[dict[str, str]] = st.session_state["review_log"]
    if not review_log:
        st.info("No reviews have been logged in this session.")
    else:
        st.dataframe(review_log, width="stretch", hide_index=True)

    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=LOG_COLUMNS)
    writer.writeheader()
    writer.writerows(review_log)
    st.download_button(
        "Download log (CSV)",
        data=output.getvalue(),
        file_name="review_log.csv",
        mime="text/csv",
    )


def main() -> None:
    st.set_page_config(page_title="Statin Outreach Prototype", layout="wide")
    st.warning(PROTOTYPE_BANNER)
    st.session_state.setdefault("review_log", [])

    page = st.sidebar.radio("Navigate", PAGES)
    try:
        data = load_demo_data()
    except DemoDataError as error:
        st.error(f"Demo data is not ready: {error}")
        st.info(
            "Place the four mock handoff files in data/demo/ to use the app. "
            "The app does not load MEPS row-level data."
        )
        return

    if page == "Overview":
        _render_overview(data)
    elif page == "Subgroups":
        _render_subgroups(data)
    elif page == "Patient view":
        _render_patient_view(data)
    else:
        _render_answer_and_log(data)


if __name__ == "__main__":
    main()
