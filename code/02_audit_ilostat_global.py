"""Audit the matched ILOSTAT tables proposed for the global paper."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "ilostat"
PROCESSED_DIR = ROOT / "data" / "processed" / "ilostat"

EARNINGS_FILE = RAW_DIR / "EAR_EMTA_SEX_EDU_NB_A.csv.gz"
EMPLOYMENT_FILE = RAW_DIR / "EMP_TEMP_SEX_STE_EDU_NB_A.csv.gz"

EDUCATION = [
    "EDU_AGGREGATE_LTB",
    "EDU_AGGREGATE_BAS",
    "EDU_AGGREGATE_INT",
    "EDU_AGGREGATE_ADV",
]


def longest_consecutive_run(years: pd.Series) -> int:
    ordered = sorted(set(int(year) for year in years))
    if not ordered:
        return 0
    longest = current = 1
    for previous, year in zip(ordered, ordered[1:]):
        current = current + 1 if year == previous + 1 else 1
        longest = max(longest, current)
    return longest


def absolute_error_summary(values: pd.Series) -> dict[str, float | int]:
    absolute = values.dropna().abs()
    return {
        "comparisons": int(absolute.size),
        "median_absolute_relative_error": float(absolute.median()),
        "p90_absolute_relative_error": float(absolute.quantile(0.9)),
        "maximum_absolute_relative_error": float(absolute.max()),
    }


def audit() -> dict[str, object]:
    earnings_raw = pd.read_csv(EARNINGS_FILE)
    employment_raw = pd.read_csv(EMPLOYMENT_FILE)

    earnings = earnings_raw[
        (earnings_raw["sex"] == "SEX_T")
        & earnings_raw["classif1"].isin(EDUCATION)
    ].copy()
    employment = employment_raw[
        (employment_raw["sex"] == "SEX_T")
        & (employment_raw["classif1"] == "STE_AGGREGATE_EES")
        & employment_raw["classif2"].isin(EDUCATION)
    ].copy()

    earnings_key = ["ref_area", "source", "time", "classif1"]
    employment_key = ["ref_area", "source", "time", "classif2"]

    matched = earnings.merge(
        employment,
        left_on=earnings_key,
        right_on=employment_key,
        suffixes=("_earn", "_emp"),
        validate="one_to_one",
    )

    coverage = (
        matched.groupby(
            [
                "ref_area",
                "ref_area.label_earn",
                "source",
                "source.label_earn",
                "time",
            ],
            as_index=False,
        )
        .agg(education_groups=("classif1_earn", "nunique"))
        .query("education_groups == 4")
    )

    country_sources = (
        coverage.groupby(
            [
                "ref_area",
                "ref_area.label_earn",
                "source",
                "source.label_earn",
            ],
            as_index=False,
        )
        .agg(
            n_years=("time", "nunique"),
            first_year=("time", "min"),
            last_year=("time", "max"),
            longest_consecutive_run=("time", longest_consecutive_run),
        )
        .rename(
            columns={
                "ref_area.label_earn": "country",
                "source.label_earn": "source_label",
            }
        )
    )

    best_panels = (
        country_sources.sort_values(
            ["ref_area", "n_years", "longest_consecutive_run", "last_year"],
            ascending=[True, False, False, False],
        )
        .drop_duplicates("ref_area")
        .sort_values(["n_years", "ref_area"], ascending=[False, True])
    )

    earnings_total = earnings_raw[
        (earnings_raw["sex"] == "SEX_T")
        & (earnings_raw["classif1"] == "EDU_AGGREGATE_TOTAL")
    ][["ref_area", "source", "time", "obs_value"]].rename(
        columns={"obs_value": "published_total_earnings"}
    )
    employment_total = employment_raw[
        (employment_raw["sex"] == "SEX_T")
        & (employment_raw["classif1"] == "STE_AGGREGATE_EES")
        & (employment_raw["classif2"] == "EDU_AGGREGATE_TOTAL")
    ][["ref_area", "source", "time", "obs_value"]].rename(
        columns={"obs_value": "published_total_employees"}
    )
    employment_unknown = employment_raw[
        (employment_raw["sex"] == "SEX_T")
        & (employment_raw["classif1"] == "STE_AGGREGATE_EES")
        & (employment_raw["classif2"] == "EDU_AGGREGATE_X")
    ][["ref_area", "source", "time", "obs_value"]].rename(
        columns={"obs_value": "unknown_education_employees"}
    )

    matched["weighted_payroll"] = (
        matched["obs_value_earn"] * matched["obs_value_emp"]
    )
    reconstruction = (
        matched.groupby(["ref_area", "source", "time"], as_index=False)
        .agg(
            education_groups=("classif1_earn", "nunique"),
            stated_education_employees=("obs_value_emp", "sum"),
            weighted_payroll=("weighted_payroll", "sum"),
        )
        .query("education_groups == 4")
    )
    reconstruction["reconstructed_earnings"] = (
        reconstruction["weighted_payroll"]
        / reconstruction["stated_education_employees"]
    )
    reconstruction = (
        reconstruction.merge(
            earnings_total,
            on=["ref_area", "source", "time"],
            how="left",
            validate="one_to_one",
        )
        .merge(
            employment_total,
            on=["ref_area", "source", "time"],
            how="left",
            validate="one_to_one",
        )
        .merge(
            employment_unknown,
            on=["ref_area", "source", "time"],
            how="left",
            validate="one_to_one",
        )
    )
    reconstruction["unknown_education_employees"] = reconstruction[
        "unknown_education_employees"
    ].fillna(0)
    reconstruction["relative_reconstruction_error"] = (
        reconstruction["reconstructed_earnings"]
        - reconstruction["published_total_earnings"]
    ) / reconstruction["published_total_earnings"]
    reconstruction["unknown_education_share"] = (
        reconstruction["unknown_education_employees"]
        / reconstruction["published_total_employees"]
    )

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    country_sources.to_csv(
        PROCESSED_DIR / "country_source_coverage.csv", index=False
    )
    best_panels.to_csv(PROCESSED_DIR / "best_country_panels.csv", index=False)
    reconstruction.to_csv(
        PROCESSED_DIR / "total_reconstruction_audit.csv", index=False
    )

    summary: dict[str, object] = {
        "raw_rows": {
            "earnings": int(len(earnings_raw)),
            "employment": int(len(employment_raw)),
        },
        "filtered_rows": {
            "earnings": int(len(earnings)),
            "employment": int(len(employment)),
        },
        "duplicate_keys": {
            "earnings": int(earnings.duplicated(earnings_key, keep=False).sum()),
            "employment": int(
                employment.duplicated(employment_key, keep=False).sum()
            ),
        },
        "complete_country_source_years": int(len(coverage)),
        "countries_with_any_complete_year": int(best_panels["ref_area"].nunique()),
        "countries_by_minimum_years": {
            str(years): int((best_panels["n_years"] >= years).sum())
            for years in [2, 5, 10, 15]
        },
        "countries_by_minimum_consecutive_run": {
            str(years): int(
                (best_panels["longest_consecutive_run"] >= years).sum()
            )
            for years in [2, 5, 10, 15]
        },
        "countries_with_latest_year_2019_or_later": int(
            (best_panels["last_year"] >= 2019).sum()
        ),
        "published_total_reconstruction": absolute_error_summary(
            reconstruction["relative_reconstruction_error"]
        ),
        "unknown_education_share": {
            "comparisons": int(
                reconstruction["unknown_education_share"].notna().sum()
            ),
            "median": float(
                reconstruction["unknown_education_share"].median()
            ),
            "p90": float(
                reconstruction["unknown_education_share"].quantile(0.9)
            ),
            "maximum": float(
                reconstruction["unknown_education_share"].max()
            ),
        },
    }

    with (PROCESSED_DIR / "audit_summary.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)

    return summary


if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
