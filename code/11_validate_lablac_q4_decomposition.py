"""Independent validation for the country-level LABLAC Q4 results."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "processed" / "lablac_q4_decomposition"
TOLERANCE = 1e-9


def maximum_absolute(values: pd.Series) -> float:
    return float(values.abs().max()) if len(values) else 0.0


def validate() -> dict[str, object]:
    countries = pd.read_csv(OUTPUT_DIR / "country_decompositions.csv")
    groups = pd.read_csv(
        OUTPUT_DIR / "country_education_components.csv"
    )
    descriptives = pd.read_csv(
        OUTPUT_DIR / "country_endpoint_descriptives.csv"
    )
    candidates = pd.read_csv(
        OUTPUT_DIR / "source_year_candidates.csv"
    )
    selected = pd.read_csv(OUTPUT_DIR / "selected_endpoints.csv")
    source_match = json.loads(
        (OUTPUT_DIR / "equitylab_source_match.json").read_text(
            encoding="utf-8"
        )
    )

    complete = candidates[candidates["complete"]].copy()
    expected_bounds = complete.groupby("country").agg(
        expected_start_year=("year", "min"),
        expected_end_year=("year", "max"),
    )
    actual_bounds = countries.set_index("country")[
        ["start_year", "end_year"]
    ]
    bounds = actual_bounds.join(
        expected_bounds,
        how="outer",
        validate="one_to_one",
    )

    group_sums = groups.groupby("country").agg(
        share_0=("share_0", "sum"),
        share_1=("share_1", "sum"),
        education_component=(
            "education_component_usd_2017_ppp",
            "sum",
        ),
        within_component=(
            "within_income_component_usd_2017_ppp",
            "sum",
        ),
    )
    country_indexed = countries.set_index("country")
    group_check = country_indexed.join(
        group_sums,
        how="outer",
        validate="one_to_one",
    )

    checks = {
        "country_rows": int(len(countries)),
        "country_key_duplicates": int(
            countries.duplicated("country", keep=False).sum()
        ),
        "group_key_duplicates": int(
            groups.duplicated(
                ["country", "education"], keep=False
            ).sum()
        ),
        "descriptive_key_duplicates": int(
            descriptives.duplicated(
                ["country", "endpoint", "education"],
                keep=False,
            ).sum()
        ),
        "selected_key_duplicates": int(
            selected.duplicated(
                ["country", "endpoint"], keep=False
            ).sum()
        ),
        "selected_rows": int(len(selected)),
        "group_rows": int(len(groups)),
        "descriptive_rows": int(len(descriptives)),
        "all_selected_periods_q4": bool(
            selected["period"].str.endswith("-Q4").all()
        ),
        "endpoint_years_are_oldest_and_newest_q4": bool(
            bounds["start_year"]
            .eq(bounds["expected_start_year"])
            .all()
            and bounds["end_year"]
            .eq(bounds["expected_end_year"])
            .all()
        ),
        "maximum_initial_share_sum_error": maximum_absolute(
            group_check["share_0"] - 1
        ),
        "maximum_final_share_sum_error": maximum_absolute(
            group_check["share_1"] - 1
        ),
        "maximum_country_identity_error": maximum_absolute(
            countries["change_usd_2017_ppp"]
            - countries["education_component_usd_2017_ppp"]
            - countries["within_income_component_usd_2017_ppp"]
        ),
        "maximum_group_education_sum_error": maximum_absolute(
            group_check["education_component"]
            - group_check["education_component_usd_2017_ppp"]
        ),
        "maximum_group_within_sum_error": maximum_absolute(
            group_check["within_component"]
            - group_check["within_income_component_usd_2017_ppp"]
        ),
        "finite_country_results": bool(
            np.isfinite(
                countries[
                    [
                        "synthetic_income_0_usd_2017_ppp",
                        "synthetic_income_1_usd_2017_ppp",
                        "percent_change",
                        "education_contribution_percent_initial",
                        "within_income_contribution_percent_initial",
                    ]
                ].to_numpy()
            ).all()
        ),
        "positive_synthetic_incomes": bool(
            countries[
                [
                    "synthetic_income_0_usd_2017_ppp",
                    "synthetic_income_1_usd_2017_ppp",
                ]
            ]
            .gt(0)
            .all()
            .all()
        ),
        "equitylab_exact_set_match": bool(
            source_match["exact_set_match"]
        ),
        "equitylab_only_attached_rows": int(
            source_match["only_attached_count"]
        ),
        "equitylab_only_repository_rows": int(
            source_match["only_repository_count"]
        ),
    }

    passed = bool(
        checks["country_rows"] == 14
        and checks["country_key_duplicates"] == 0
        and checks["group_key_duplicates"] == 0
        and checks["descriptive_key_duplicates"] == 0
        and checks["selected_key_duplicates"] == 0
        and checks["selected_rows"] == 28
        and checks["group_rows"] == 42
        and checks["descriptive_rows"] == 84
        and checks["all_selected_periods_q4"]
        and checks["endpoint_years_are_oldest_and_newest_q4"]
        and checks["maximum_initial_share_sum_error"] <= TOLERANCE
        and checks["maximum_final_share_sum_error"] <= TOLERANCE
        and checks["maximum_country_identity_error"] <= TOLERANCE
        and checks["maximum_group_education_sum_error"] <= TOLERANCE
        and checks["maximum_group_within_sum_error"] <= TOLERANCE
        and checks["finite_country_results"]
        and checks["positive_synthetic_incomes"]
        and checks["equitylab_exact_set_match"]
        and checks["equitylab_only_attached_rows"] == 0
        and checks["equitylab_only_repository_rows"] == 0
    )
    result = {
        "status": "PASS" if passed else "FAIL",
        "tolerance": TOLERANCE,
        "checks": checks,
    }
    (OUTPUT_DIR / "independent_validation_summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result


if __name__ == "__main__":
    summary = validate()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["status"] != "PASS":
        raise SystemExit(1)
