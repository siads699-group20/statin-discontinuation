from __future__ import annotations

import re
import shutil
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
import pyreadstat

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
LONGITUDINAL_FILE = "h252dta.zip"
PRESCRIPTION_FILES = ("h239adta.zip", "h248adta.zip")
PRESCRIPTION_COST_FIELDS = {
    "h239adta.zip": "RXSF22X",
    "h248adta.zip": "RXSF23X",
}
CONDITION_FILES = ("h241dta.zip", "h249dta.zip")
ROUNDS = range(1, 6)
JOIN_KEYS = ["DUPERSID", "ROUND"]
CONDITION_KEY = ["DUPERSID", "CONDIDX"]
PURCHASE_KEY = ["DUPERSID", "RXRECIDX"]

PERSON_COLUMNS = (
    "DUPERSID",
    "PANEL",
    "ALL5RDS",
    "DIED",
    "INST",
    "MILITARY",
    "LEFTUS",
    "SEX",
    "RACETHX",
    "HISPANX",
    "EDUCYR",
    "HIDEG",
    "HWELLSPK",
    "LONGWT",
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
ROUND_FIELDS = {
    "AGE": "AGE{round}X",
    "RTHLTH": "RTHLTH{round}",
    "MNHLTH": "MNHLTH{round}",
    "INS": "INS{round}X",
    "MCARE": "MCARE{round}",
    "MCAID": "MCAID{round}",
    "PRIVAT": "PRIVAT{round}",
    "PMEDIN": "PMEDIN{round}",
    "ELGRND": "ELGRND{round}",
    "INSCOP": "INSCOP{round}",
    "BEGRFM": "BEGRFM{round}",
    "BEGRFY": "BEGRFY{round}",
    "ENDRFM": "ENDRFM{round}",
    "ENDRFY": "ENDRFY{round}",
}
def medicare_rx_field(round_number: int) -> str:
    return f"MCRPD{round_number}X"


LONGITUDINAL_COLUMNS = tuple(dict.fromkeys(
    PERSON_COLUMNS
    + tuple(
        column
        for round_number in ROUNDS
        for column in (
            *(field.format(round=round_number) for field in ROUND_FIELDS.values()),
            *(
                [medicare_rx_field(round_number)]
                if round_number < 5
                else []
            ),
        )
    )
))
PRESCRIPTION_HISTORY_COLUMNS = tuple(dict.fromkeys(
    PRESCRIPTION_COLUMNS + ("DRUGIDX", "RXNAME")
))
CONDITION_COLUMNS = (
    "DUPERSID",
    "PANEL",
    "CONDIDX",
    "CONDRN",
    "ICD10CDX",
    "CCSR1X",
    "CCSR2X",
    "CCSR3X",
    "CCSR4X",
    "CRND1",
    "CRND2",
    "CRND3",
    "CRND4",
    "CRND5",
)
STATIN_BRANDS = {
    "ATORVASTATIN": ("LIPITOR", "CADUET", "LIPTRUZET"),
    "ROSUVASTATIN": ("CRESTOR", "EZALLOR SPRINKLE", "ROSZET"),
    "SIMVASTATIN": ("ZOCOR", "VYTORIN", "SIMCOR"),
    "PRAVASTATIN": ("PRAVACHOL",),
    "LOVASTATIN": ("MEVACOR", "ALTOPREV", "ADVICOR"),
    "FLUVASTATIN": ("LESCOL", "LESCOL XL"),
    "PITAVASTATIN": ("LIVALO", "ZYPITAMAG"),
}
STATIN_GENERIC_NAMES = tuple(STATIN_BRANDS)
BRAND_TO_GENERIC = {
    brand: generic
    for generic, brands in STATIN_BRANDS.items()
    for brand in brands
}


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
        with tempfile.TemporaryDirectory(prefix="meps_linkage_") as temp_dir:
            stata_path = Path(temp_dir) / Path(stata_files[0]).name
            with archive.open(stata_files[0]) as source, stata_path.open("wb") as target:
                shutil.copyfileobj(source, target)
            frame, metadata = pyreadstat.read_dta(
                str(stata_path), usecols=list(columns)
            )

    missing = set(columns).difference(metadata.column_names)
    if missing:
        raise ValueError(f"{filename} is missing columns: {sorted(missing)}")
    return frame


def mark_statin_purchases(prescriptions: pd.DataFrame) -> pd.DataFrame:
    """Flag statin records and standardize recognized brands to generic names."""
    marked = prescriptions.copy()
    class_match = marked["TC1S1_1"].eq(173) | marked["TC2S1_1"].eq(173)
    standardized = marked.apply(
        lambda row: standardize_statin_name(row["RXDRGNAM"], row["RXNAME"]),
        axis=1,
        result_type="expand",
    )
    marked["standardized_statin"] = standardized[0]
    marked["mapping_source"] = standardized[1]
    marked["is_statin"] = class_match | marked["standardized_statin"].ne("")
    marked.loc[
        class_match & marked["standardized_statin"].eq(""),
        "mapping_source",
    ] = "class_code_only"
    return marked


def names_in_text(value: object, names: tuple[str, ...]) -> set[str]:
    text = re.sub(r"[^A-Z0-9]+", " ", str(value).upper()).strip()
    return {
        name
        for name in names
        if re.search(rf"\b{re.escape(name)}\b", text)
    }


def standardize_statin_name(
    generic_name: object,
    reported_name: object,
) -> tuple[str, str]:
    generic_matches = names_in_text(generic_name, STATIN_GENERIC_NAMES)
    if generic_matches:
        return "; ".join(sorted(generic_matches)), "generic_name"

    reported_generic_matches = names_in_text(
        reported_name, STATIN_GENERIC_NAMES
    )
    if reported_generic_matches:
        return "; ".join(sorted(reported_generic_matches)), "generic_name"

    reported_brands = names_in_text(reported_name, tuple(BRAND_TO_GENERIC))
    brand_matches = {BRAND_TO_GENERIC[brand] for brand in reported_brands}
    if brand_matches:
        return "; ".join(sorted(brand_matches)), "brand_name"

    return "", ""


def make_person_rounds(longitudinal: pd.DataFrame) -> pd.DataFrame:
    missing = set(LONGITUDINAL_COLUMNS).difference(longitudinal.columns)
    if missing:
        raise ValueError(f"Longitudinal file is missing columns: {sorted(missing)}")
    if longitudinal["DUPERSID"].isna().any():
        raise ValueError("Longitudinal file has missing DUPERSID values")
    if longitudinal["DUPERSID"].duplicated().any():
        raise ValueError("Longitudinal file has duplicate DUPERSID values")

    panel = longitudinal.loc[longitudinal["PANEL"].eq(27)]
    rows = []
    for round_number in ROUNDS:
        round_frame = panel.loc[:, PERSON_COLUMNS].copy()
        round_frame["ROUND"] = round_number
        for output_name, source_name in ROUND_FIELDS.items():
            column = source_name.format(round=round_number)
            round_frame[output_name] = panel[column].to_numpy()
        round_frame["MCRPD"] = (
            panel[medicare_rx_field(round_number)].to_numpy()
            if round_number < 5
            else pd.NA
        )
        rows.append(round_frame)

    result = pd.concat(rows, ignore_index=True)
    if result.duplicated(JOIN_KEYS).any():
        raise ValueError("Longitudinal person-round keys are not unique")
    return result


def clean_names(values: pd.Series) -> str:
    names = set()
    for value in values.dropna():
        for name in str(value).split(";"):
            name = name.strip().upper()
            if name not in {"", "-1", "-15"}:
                names.add(name)
    return "; ".join(sorted(names))


def summarize_prescriptions(
    files: tuple[pd.DataFrame, ...],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    tagged_files = []
    for index, frame in enumerate(files):
        tagged = frame.copy()
        if "SOURCE_FILE" not in tagged:
            tagged["SOURCE_FILE"] = (
                PRESCRIPTION_FILES[index]
                if index < len(PRESCRIPTION_FILES)
                else f"prescription_file_{index + 1}"
            )
        if "RXSF" not in tagged:
            cost_fields = {
                field: field
                for field in PRESCRIPTION_COST_FIELDS.values()
                if field in tagged
            }
            if len(cost_fields) != 1:
                raise ValueError(
                    "Prescription records must contain normalized RXSF or "
                    "exactly one year-specific RXSF field"
                )
            tagged["RXSF"] = tagged[cost_fields.popitem()[0]]
        tagged["SOURCE_PRIORITY"] = tagged["SOURCE_FILE"].map(
            {"h239adta.zip": 0, "h248adta.zip": 1}
        ).fillna(index)
        tagged_files.append(tagged)
    records = pd.concat(tagged_files, ignore_index=True)
    missing = set(PRESCRIPTION_HISTORY_COLUMNS).difference(records.columns)
    if missing:
        raise ValueError(f"Prescription files are missing columns: {sorted(missing)}")

    panel_records = records.loc[records["PANEL"].eq(27)].copy()
    round_records = panel_records.loc[panel_records["PURCHRD"].isin(ROUNDS)].copy()
    if round_records[list(PURCHASE_KEY) + ["PURCHRD"]].isna().any().any():
        raise ValueError("Panel 27 prescriptions have missing person, round, or record ID")

    round_records = mark_statin_purchases(round_records)
    duplicate_mask = round_records.duplicated(list(PURCHASE_KEY), keep=False)
    duplicate_records = round_records.loc[duplicate_mask]
    if not duplicate_records.empty:
        duplicate_groups = duplicate_records.groupby(PURCHASE_KEY, dropna=False)
        if duplicate_groups["PURCHRD"].nunique(dropna=False).gt(1).any():
            raise ValueError("A repeated prescription ID has conflicting rounds")

    statin_conflicts = int(
        duplicate_records.groupby(PURCHASE_KEY, dropna=False)["is_statin"]
        .nunique(dropna=False)
        .gt(1)
        .sum()
    )
    statin_duplicate_records = duplicate_records.loc[
        duplicate_records.groupby(PURCHASE_KEY, dropna=False)["is_statin"]
        .transform("any")
    ]
    statin_cost_conflicts = int(
        statin_duplicate_records.groupby(PURCHASE_KEY, dropna=False)["RXSF"]
        .nunique(dropna=False)
        .gt(1)
        .sum()
    )
    round_records = round_records.sort_values(
        "SOURCE_PRIORITY", kind="stable"
    )
    purchases = round_records.groupby(
        PURCHASE_KEY, as_index=False, dropna=False
    ).agg(
        PURCHRD=("PURCHRD", "first"),
        DRUGIDX=("DRUGIDX", "first"),
        is_statin=("is_statin", "any"),
        RXSF=("RXSF", "last"),
        RXSF_SOURCE=("SOURCE_FILE", "last"),
        standardized_statin=("standardized_statin", clean_names),
        mapping_source=("mapping_source", clean_names),
        source_files=("SOURCE_FILE", clean_names),
        RXDRGNAM=("RXDRGNAM", clean_names),
        RXNAME=("RXNAME", clean_names),
        TC1S1_1=("TC1S1_1", clean_names),
        TC2S1_1=("TC2S1_1", clean_names),
    )
    summary = purchases.groupby(
        ["DUPERSID", "PURCHRD"], as_index=False, dropna=False
    ).agg(
        rx_purchase_count=("RXRECIDX", "nunique"),
        distinct_drug_count=("DRUGIDX", "nunique"),
        statin_purchase_count=("is_statin", "sum"),
        standardized_statins=("standardized_statin", clean_names),
        generic_drug_names=("RXDRGNAM", clean_names),
        reported_drug_names=("RXNAME", clean_names),
    ).rename(columns={"PURCHRD": "ROUND"})
    statin_costs = purchases.loc[purchases["is_statin"]].groupby(
        ["DUPERSID", "PURCHRD"], as_index=False, dropna=False
    ).agg(
        statin_rx_cost=("RXSF", lambda amounts: amounts.sum(min_count=1))
    ).rename(columns={"PURCHRD": "ROUND"})
    summary = summary.merge(
        statin_costs,
        on=["DUPERSID", "ROUND"],
        how="left",
        validate="one_to_one",
    )
    summary.loc[summary["statin_purchase_count"].eq(0), "statin_rx_cost"] = 0.0
    statin_purchases = purchases.loc[
        purchases["is_statin"],
        [
            "DUPERSID",
            "PURCHRD",
            "RXRECIDX",
            "DRUGIDX",
            "RXSF",
            "RXSF_SOURCE",
            "standardized_statin",
            "mapping_source",
            "source_files",
            "RXDRGNAM",
            "RXNAME",
            "TC1S1_1",
            "TC2S1_1",
        ],
    ].rename(columns={"PURCHRD": "ROUND"})
    stats = {
        "prescription_rows_in_source_files": len(records),
        "prescription_rows_for_panel_27": len(panel_records),
        "prescription_rows_in_rounds_1_to_5": len(round_records),
        "duplicate_prescription_rows_merged": len(round_records) - len(purchases),
        "duplicate_purchase_ids_with_conflicting_statin_flags": statin_conflicts,
        "unique_prescription_records": len(purchases),
        "unique_statin_purchases": len(statin_purchases),
        "mapped_statin_purchases": int(statin_purchases["standardized_statin"].ne("").sum()),
        "class_code_statin_purchases_without_name_mapping": int(
            (statin_purchases["mapping_source"] == "CLASS_CODE_ONLY").sum()
        ),
        "statin_purchase_ids_with_conflicting_duplicate_costs": statin_cost_conflicts,
        "statin_purchases_missing_out_of_pocket_cost": int(
            statin_purchases["RXSF"].isna().sum()
        ),
    }
    return summary, statin_purchases, stats


def summarize_conditions(
    files: tuple[pd.DataFrame, ...],
) -> tuple[pd.DataFrame, dict[str, int]]:
    records = pd.concat(files, ignore_index=True)
    missing = set(CONDITION_COLUMNS).difference(records.columns)
    if missing:
        raise ValueError(f"Condition files are missing columns: {sorted(missing)}")

    panel_records = records.loc[records["PANEL"].eq(27)].copy()
    if panel_records[CONDITION_KEY].isna().any().any():
        raise ValueError("Panel 27 conditions have missing person or condition IDs")

    duplicate_rows = int(panel_records.duplicated(CONDITION_KEY).sum())
    condition_groups = panel_records.groupby(
        CONDITION_KEY, as_index=False, dropna=False
    )
    conditions = condition_groups.agg(
        CONDRN=("CONDRN", "first"),
        ICD10CDX=("ICD10CDX", clean_names),
        CCSR1X=("CCSR1X", clean_names),
        CCSR2X=("CCSR2X", clean_names),
        CCSR3X=("CCSR3X", clean_names),
        CCSR4X=("CCSR4X", clean_names),
        **{
            f"CRND{round_number}": (f"CRND{round_number}", "max")
            for round_number in ROUNDS
        },
    )

    round_rows = []
    for round_number in ROUNDS:
        active = conditions.loc[conditions[f"CRND{round_number}"].eq(1)].copy()
        active["ROUND"] = round_number
        active["new_condition"] = active["CONDRN"].eq(round_number)
        active["ccsr_codes"] = active[
            ["CCSR1X", "CCSR2X", "CCSR3X", "CCSR4X"]
        ].apply(clean_names, axis=1)
        round_rows.append(active)

    active_conditions = pd.concat(round_rows, ignore_index=True)
    summary = active_conditions.groupby(
        ["DUPERSID", "ROUND"], as_index=False, dropna=False
    ).agg(
        active_condition_count=("CONDIDX", "nunique"),
        new_condition_count=("new_condition", "sum"),
        active_icd10_codes=("ICD10CDX", clean_names),
        active_ccsr_codes=("ccsr_codes", clean_names),
    )
    return summary, {
        "condition_rows_in_source_files": len(records),
        "condition_rows_for_panel_27": len(panel_records),
        "duplicate_condition_rows_merged": duplicate_rows,
        "unique_panel_27_conditions": len(conditions),
    }


def left_join_with_audit(
    history: pd.DataFrame,
    summary: pd.DataFrame,
    name: str,
) -> tuple[pd.DataFrame, dict[str, int | str], pd.DataFrame]:
    if summary.duplicated(JOIN_KEYS).any():
        raise ValueError(f"{name} summary has duplicate person-round keys")

    joined = history.merge(
        summary,
        on=JOIN_KEYS,
        how="left",
        validate="one_to_one",
        indicator=True,
    )
    matched = int(joined["_merge"].eq("both").sum())
    unmatched_left = int(joined["_merge"].eq("left_only").sum())
    unmatched_keys = summary[JOIN_KEYS].merge(
        history[JOIN_KEYS].drop_duplicates(),
        on=JOIN_KEYS,
        how="left",
        validate="one_to_one",
        indicator=True,
    )
    unmatched_keys = unmatched_keys.loc[
        unmatched_keys["_merge"].eq("left_only"), JOIN_KEYS
    ].copy()
    unmatched_keys.insert(0, "join", name)
    audit = {
        "join": name,
        "left_rows_before": len(history),
        "right_rows": len(summary),
        "rows_after": len(joined),
        "matched_left_rows": matched,
        "unmatched_left_rows": unmatched_left,
        "unmatched_right_rows": len(unmatched_keys),
        "left_rows_dropped": len(history) - len(joined),
    }
    if len(joined) != len(history):
        raise ValueError(f"{name} join changed the number of history rows")
    return joined.drop(columns="_merge"), audit, unmatched_keys


def build_person_round_history(
    longitudinal: pd.DataFrame,
    prescription_files: tuple[pd.DataFrame, ...],
    condition_files: tuple[pd.DataFrame, ...],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    history = make_person_rounds(longitudinal)
    (
        prescription_summary,
        statin_purchases,
        prescription_quality,
    ) = summarize_prescriptions(prescription_files)
    condition_summary, condition_quality = summarize_conditions(condition_files)

    history, prescription_audit, unmatched_prescriptions = left_join_with_audit(
        history, prescription_summary, "longitudinal + prescriptions"
    )
    history, condition_audit, unmatched_conditions = left_join_with_audit(
        history, condition_summary, "longitudinal + prescriptions + conditions"
    )
    for column in (
        "rx_purchase_count",
        "distinct_drug_count",
        "statin_purchase_count",
        "active_condition_count",
        "new_condition_count",
    ):
        history[column] = history[column].fillna(0).astype("int64")
    for column in (
        "generic_drug_names",
        "reported_drug_names",
        "standardized_statins",
        "active_icd10_codes",
        "active_ccsr_codes",
    ):
        history[column] = history[column].fillna("")
    history.loc[
        history["statin_purchase_count"].eq(0), "statin_rx_cost"
    ] = 0.0

    join_audit = pd.DataFrame([prescription_audit, condition_audit])
    unmatched_keys = pd.concat(
        [unmatched_prescriptions, unmatched_conditions], ignore_index=True
    )
    quality = pd.DataFrame([
        *prescription_quality.items(),
        *condition_quality.items(),
        ("longitudinal_panel_27_people", history["DUPERSID"].nunique()),
        ("person_round_rows", len(history)),
    ], columns=("metric", "value"))
    return history, join_audit, quality, unmatched_keys, statin_purchases


def main() -> int:
    longitudinal = read_meps_file(LONGITUDINAL_FILE, LONGITUDINAL_COLUMNS)
    prescriptions = []
    for filename in PRESCRIPTION_FILES:
        cost_field = PRESCRIPTION_COST_FIELDS[filename]
        frame = read_meps_file(
            filename, PRESCRIPTION_HISTORY_COLUMNS + (cost_field,)
        )
        frame = frame.rename(columns={cost_field: "RXSF"})
        frame["SOURCE_FILE"] = filename
        prescriptions.append(frame)
    conditions = tuple(
        read_meps_file(filename, CONDITION_COLUMNS)
        for filename in CONDITION_FILES
    )
    history, join_audit, quality, unmatched_keys, statin_purchases = (
        build_person_round_history(
            longitudinal, tuple(prescriptions), conditions
        )
    )

    output_dir = ROOT / "data" / "interim"
    output_dir.mkdir(parents=True, exist_ok=True)
    history.to_csv(output_dir / "person_round_history.csv", index=False)
    join_audit.to_csv(output_dir / "join_audit.csv", index=False)
    quality.to_csv(output_dir / "linkage_data_quality.csv", index=False)
    unmatched_keys.to_csv(output_dir / "unmatched_linkage_keys.csv", index=False)
    statin_purchases.to_csv(output_dir / "statin_purchases.csv", index=False)

    print(f"Person-round rows: {len(history):,}")
    print(join_audit.to_string(index=False))
    print(quality.to_string(index=False))
    print(f"Outputs written to {output_dir.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
