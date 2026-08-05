"""Independent checks for the common-window regional LABLAC decomposition."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = (
    ROOT / "data" / "processed" / "lablac_q4_regional_decomposition"
)
TOLERANCE = 1e-9
START_YEAR = 2017
END_YEAR = 2022
YEARS_ELAPSED = END_YEAR - START_YEAR


def maximum_absolute(values: pd.Series | np.ndarray) -> float:
    return float(np.max(np.abs(np.asarray(values, dtype=float))))


def main() -> None:
    cells = pd.read_csv(OUTPUT_DIR / "selected_endpoint_cells.csv")
    countries = pd.read_csv(
        OUTPUT_DIR / "country_decompositions_2017_2022.csv"
    )
    weights = pd.read_csv(OUTPUT_DIR / "country_weights.csv")
    aggregates = pd.read_csv(
        OUTPUT_DIR / "regional_decompositions.csv"
    )
    descriptives = pd.read_csv(
        OUTPUT_DIR / "regional_descriptives.csv"
    )

    cells["payroll_check"] = (
        cells["workers"] * cells["income_usd_2017_ppp"]
    )
    pooled = cells.groupby("endpoint").agg(
        workers=("workers", "sum"),
        payroll=("payroll_check", "sum"),
    )
    pooled["income"] = pooled["payroll"] / pooled["workers"]

    changing = aggregates.set_index("aggregation").loc[
        "changing_employment_weights"
    ]
    fixed = aggregates.set_index("aggregation").loc[
        "fixed_employment_weights"
    ]
    equal = aggregates.set_index("aggregation").loc[
        "equal_country_weights"
    ]

    country_data = countries.merge(
        weights[
            [
                "country",
                "weight_0",
                "weight_1",
                "midpoint_employment_weight",
                "equal_country_weight",
            ]
        ],
        on="country",
        how="inner",
        validate="one_to_one",
    )
    average_weight = (
        country_data["weight_0"] + country_data["weight_1"]
    ) / 2

    recomputed = {
        "fixed_mean_0": float(
            (
                country_data["midpoint_employment_weight"]
                * country_data["synthetic_income_0_usd_2017_ppp"]
            ).sum()
        ),
        "fixed_mean_1": float(
            (
                country_data["midpoint_employment_weight"]
                * country_data["synthetic_income_1_usd_2017_ppp"]
            ).sum()
        ),
        "fixed_education": float(
            (
                country_data["midpoint_employment_weight"]
                * country_data["education_component_usd_2017_ppp"]
            ).sum()
        ),
        "fixed_within": float(
            (
                country_data["midpoint_employment_weight"]
                * country_data["within_income_component_usd_2017_ppp"]
            ).sum()
        ),
        "equal_mean_0": float(
            (
                country_data["equal_country_weight"]
                * country_data["synthetic_income_0_usd_2017_ppp"]
            ).sum()
        ),
        "equal_mean_1": float(
            (
                country_data["equal_country_weight"]
                * country_data["synthetic_income_1_usd_2017_ppp"]
            ).sum()
        ),
        "changing_education": float(
            (
                average_weight
                * country_data["education_component_usd_2017_ppp"]
            ).sum()
        ),
        "changing_within": float(
            (
                average_weight
                * country_data[
                    "within_income_component_usd_2017_ppp"
                ]
            ).sum()
        ),
        "changing_country_composition": float(
            (
                (
                    (
                        country_data[
                            "synthetic_income_0_usd_2017_ppp"
                        ]
                        + country_data[
                            "synthetic_income_1_usd_2017_ppp"
                        ]
                    )
                    / 2
                )
                * (
                    country_data["weight_1"]
                    - country_data["weight_0"]
                )
            ).sum()
        ),
    }

    expected_cagr = 100 * (
        (
            aggregates["mean_income_1_usd_2017_ppp"]
            / aggregates["mean_income_0_usd_2017_ppp"]
        )
        ** (1 / YEARS_ELAPSED)
        - 1
    )
    annualized_sum = (
        aggregates[
            "annualized_country_composition_percentage_points"
        ]
        + aggregates[
            "annualized_education_contribution_percentage_points"
        ]
        + aggregates[
            "annualized_within_contribution_percentage_points"
        ]
    )
    group_rows = descriptives[
        descriptives["education_label"].ne("Total")
    ]
    total_row = descriptives[
        descriptives["education_label"].eq("Total")
    ].iloc[0]
    low_middle_high_payroll_0 = float(
        (
            group_rows["workers_0"]
            * group_rows["income_0_usd_2017_ppp"]
        ).sum()
    )
    low_middle_high_payroll_1 = float(
        (
            group_rows["workers_1"]
            * group_rows["income_1_usd_2017_ppp"]
        ).sum()
    )

    errors = {
        "pooled_initial_income_error": (
            changing["mean_income_0_usd_2017_ppp"]
            - pooled.loc["initial", "income"]
        ),
        "pooled_final_income_error": (
            changing["mean_income_1_usd_2017_ppp"]
            - pooled.loc["final", "income"]
        ),
        "fixed_initial_mean_error": (
            fixed["mean_income_0_usd_2017_ppp"]
            - recomputed["fixed_mean_0"]
        ),
        "fixed_final_mean_error": (
            fixed["mean_income_1_usd_2017_ppp"]
            - recomputed["fixed_mean_1"]
        ),
        "fixed_education_error": (
            fixed["education_component_usd_2017_ppp"]
            - recomputed["fixed_education"]
        ),
        "fixed_within_error": (
            fixed["within_income_component_usd_2017_ppp"]
            - recomputed["fixed_within"]
        ),
        "equal_initial_mean_error": (
            equal["mean_income_0_usd_2017_ppp"]
            - recomputed["equal_mean_0"]
        ),
        "equal_final_mean_error": (
            equal["mean_income_1_usd_2017_ppp"]
            - recomputed["equal_mean_1"]
        ),
        "changing_education_error": (
            changing["education_component_usd_2017_ppp"]
            - recomputed["changing_education"]
        ),
        "changing_within_error": (
            changing["within_income_component_usd_2017_ppp"]
            - recomputed["changing_within"]
        ),
        "changing_country_composition_error": (
            changing[
                "country_composition_component_usd_2017_ppp"
            ]
            - recomputed["changing_country_composition"]
        ),
        "total_initial_payroll_error": (
            total_row["workers_0"]
            * total_row["income_0_usd_2017_ppp"]
            - low_middle_high_payroll_0
        ),
        "total_final_payroll_error": (
            total_row["workers_1"]
            * total_row["income_1_usd_2017_ppp"]
            - low_middle_high_payroll_1
        ),
    }

    source_change_countries = sorted(
        countries.loc[~countries["same_source"], "country"].tolist()
    )
    checks = {
        "countries": int(countries["country"].nunique()),
        "cells": int(len(cells)),
        "endpoint_years": sorted(
            cells["year"].astype(int).unique().tolist()
        ),
        "three_groups_per_country_endpoint": bool(
            cells.groupby(["country", "endpoint"])["education"]
            .nunique()
            .eq(3)
            .all()
        ),
        "maximum_recomputation_error": maximum_absolute(
            np.array(list(errors.values()))
        ),
        "maximum_aggregate_identity_error": maximum_absolute(
            aggregates["residual_usd_2017_ppp"]
        ),
        "maximum_cagr_error": maximum_absolute(
            aggregates["annualized_growth_percent"] - expected_cagr
        ),
        "maximum_annualized_additivity_error": maximum_absolute(
            aggregates["annualized_growth_percent"] - annualized_sum
        ),
        "country_weight_sum_0_error": float(
            abs(weights["weight_0"].sum() - 1)
        ),
        "country_weight_sum_1_error": float(
            abs(weights["weight_1"].sum() - 1)
        ),
        "midpoint_weight_sum_error": float(
            abs(weights["midpoint_employment_weight"].sum() - 1)
        ),
        "equal_weight_sum_error": float(
            abs(weights["equal_country_weight"].sum() - 1)
        ),
        "education_share_sum_0_error": float(
            abs(group_rows["employment_share_0"].sum() - 1)
        ),
        "education_share_sum_1_error": float(
            abs(group_rows["employment_share_1"].sum() - 1)
        ),
        "source_change_countries": source_change_countries,
        "all_values_positive": bool(
            cells["workers"].gt(0).all()
            and cells["income_usd_2017_ppp"].gt(0).all()
        ),
    }
    numeric_checks = [
        value
        for key, value in checks.items()
        if key.endswith("_error")
    ]
    passed = bool(
        checks["countries"] == 14
        and checks["cells"] == 84
        and checks["endpoint_years"] == [START_YEAR, END_YEAR]
        and checks["three_groups_per_country_endpoint"]
        and checks["all_values_positive"]
        and max(numeric_checks) <= TOLERANCE
    )
    result = {
        "status": "PASS" if passed else "FAIL",
        "tolerance": TOLERANCE,
        "checks": checks,
        "recomputation_errors": errors,
    }
    with (
        OUTPUT_DIR / "independent_validation_summary.json"
    ).open("w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    if not passed:
        raise ValueError(json.dumps(result, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
