"""Independent validation checks for the global sample decomposition."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "processed" / "global_decomposition"

TOLERANCE = 1e-9


def maximum_absolute(series: pd.Series) -> float:
    return float(series.abs().max()) if len(series) else 0.0


def validate() -> dict[str, object]:
    countries = pd.read_csv(OUTPUT_DIR / "country_decompositions.csv")
    groups = pd.read_csv(
        OUTPUT_DIR / "country_education_contributions.csv"
    )
    aggregates = pd.read_csv(OUTPUT_DIR / "aggregate_decompositions.csv")
    source_audit = pd.read_csv(OUTPUT_DIR / "window_source_audit.csv")

    country_key = ["share_jump_screen", "window", "country_code"]
    group_key = country_key + ["education"]
    aggregate_key = ["share_jump_screen", "window", "aggregation"]

    duplicate_country_keys = int(
        countries.duplicated(country_key, keep=False).sum()
    )
    duplicate_group_keys = int(groups.duplicated(group_key, keep=False).sum())
    duplicate_aggregate_keys = int(
        aggregates.duplicated(aggregate_key, keep=False).sum()
    )

    group_sums = (
        groups.groupby(country_key, as_index=False)
        .agg(
            share_0=("share_0", "sum"),
            share_1=("share_1", "sum"),
            education_component=(
                "education_component_ppp_2021",
                "sum",
            ),
            within_wage_component=(
                "within_wage_component_ppp_2021",
                "sum",
            ),
        )
        .merge(
            countries[
                country_key
                + [
                    "education_component_ppp_2021",
                    "within_wage_component_ppp_2021",
                ]
            ],
            on=country_key,
            how="inner",
            validate="one_to_one",
            suffixes=("_groups", "_country"),
        )
    )

    share_sum_error = max(
        maximum_absolute(group_sums["share_0"] - 1),
        maximum_absolute(group_sums["share_1"] - 1),
    )
    education_group_sum_error = maximum_absolute(
        group_sums["education_component"]
        - group_sums["education_component_ppp_2021"]
    )
    within_group_sum_error = maximum_absolute(
        group_sums["within_wage_component"]
        - group_sums["within_wage_component_ppp_2021"]
    )

    country_identity_error = maximum_absolute(
        countries["change_ppp_2021"]
        - countries["education_component_ppp_2021"]
        - countries["within_wage_component_ppp_2021"]
    )
    aggregate_identity_error = maximum_absolute(
        aggregates["change_ppp_2021"]
        - aggregates["education_component_ppp_2021"]
        - aggregates["within_wage_component_ppp_2021"]
        - aggregates["country_composition_component_ppp_2021"]
    )

    selected = source_audit[source_audit["selected"]].copy()
    selected_quality_failures = int(
        (
            ~selected[
                [
                    "endpoint_pair",
                    "endpoints_clean",
                    "stable_currency",
                    "stable_reference_period",
                    "no_reported_break",
                    "stable_education_distribution",
                    "wdi_complete",
                    "eligible",
                ]
            ].all(axis=1)
        ).sum()
    )
    selected_sample_mismatch = int(
        len(
            selected[country_key].merge(
                countries[country_key],
                on=country_key,
                how="outer",
                indicator=True,
            ).query("_merge != 'both'")
        )
    )

    checks = {
        "duplicate_country_keys": duplicate_country_keys,
        "duplicate_group_keys": duplicate_group_keys,
        "duplicate_aggregate_keys": duplicate_aggregate_keys,
        "maximum_share_sum_error": share_sum_error,
        "maximum_education_group_sum_error": education_group_sum_error,
        "maximum_within_group_sum_error": within_group_sum_error,
        "maximum_country_identity_error": country_identity_error,
        "maximum_aggregate_identity_error": aggregate_identity_error,
        "selected_quality_failures": selected_quality_failures,
        "selected_sample_mismatch": selected_sample_mismatch,
        "finite_country_values": bool(
            np.isfinite(
                countries[
                    [
                        "mean_wage_0_ppp_2021",
                        "mean_wage_1_ppp_2021",
                        "education_component_ppp_2021",
                        "within_wage_component_ppp_2021",
                    ]
                ].to_numpy()
            ).all()
        ),
        "positive_country_mean_wages": bool(
            countries[
                ["mean_wage_0_ppp_2021", "mean_wage_1_ppp_2021"]
            ]
            .gt(0)
            .all()
            .all()
        ),
    }
    passed = (
        duplicate_country_keys == 0
        and duplicate_group_keys == 0
        and duplicate_aggregate_keys == 0
        and share_sum_error <= TOLERANCE
        and education_group_sum_error <= TOLERANCE
        and within_group_sum_error <= TOLERANCE
        and country_identity_error <= TOLERANCE
        and aggregate_identity_error <= TOLERANCE
        and selected_quality_failures == 0
        and selected_sample_mismatch == 0
        and checks["finite_country_values"]
        and checks["positive_country_mean_wages"]
    )
    summary = {
        "status": "PASS" if passed else "FAIL",
        "tolerance": TOLERANCE,
        "checks": checks,
    }
    with (OUTPUT_DIR / "validation_summary.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    return summary


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] != "PASS":
        raise SystemExit(1)
