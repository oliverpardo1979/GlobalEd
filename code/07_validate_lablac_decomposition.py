"""Independent validation checks for the LABLAC decomposition."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "processed" / "lablac_decomposition"

TOLERANCE = 1e-9
MAX_INCOME_RECONSTRUCTION_ERROR = 0.05
MAX_WORKER_RECONSTRUCTION_ERROR = 0.03


def maximum_absolute(series: pd.Series) -> float:
    return float(series.abs().max()) if len(series) else 0.0


def validate() -> dict[str, object]:
    countries = pd.read_csv(OUTPUT_DIR / "country_decompositions.csv")
    groups = pd.read_csv(
        OUTPUT_DIR / "country_education_contributions.csv"
    )
    aggregates = pd.read_csv(
        OUTPUT_DIR / "aggregate_decompositions.csv"
    )
    audit = pd.read_csv(OUTPUT_DIR / "window_source_audit.csv")

    country_key = ["window", "country"]
    group_key = country_key + ["education"]
    aggregate_key = ["window", "aggregation"]

    duplicate_country_keys = int(
        countries.duplicated(country_key, keep=False).sum()
    )
    duplicate_group_keys = int(
        groups.duplicated(group_key, keep=False).sum()
    )
    duplicate_aggregate_keys = int(
        aggregates.duplicated(aggregate_key, keep=False).sum()
    )

    group_sums = (
        groups.groupby(country_key, as_index=False)
        .agg(
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
        .merge(
            countries[
                country_key
                + [
                    "education_component_usd_2017_ppp",
                    "within_income_component_usd_2017_ppp",
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
        - group_sums["education_component_usd_2017_ppp"]
    )
    within_group_sum_error = maximum_absolute(
        group_sums["within_component"]
        - group_sums["within_income_component_usd_2017_ppp"]
    )

    country_identity_error = maximum_absolute(
        countries["change_usd_2017_ppp"]
        - countries["education_component_usd_2017_ppp"]
        - countries["within_income_component_usd_2017_ppp"]
    )
    aggregate_identity_error = maximum_absolute(
        aggregates["change_usd_2017_ppp"]
        - aggregates["education_component_usd_2017_ppp"]
        - aggregates["within_income_component_usd_2017_ppp"]
        - aggregates[
            "country_composition_component_usd_2017_ppp"
        ]
    )

    selected = audit[audit["selected"]].copy()
    selected_quality_failures = int(
        (
            ~selected[
                [
                    "both_endpoint_years",
                    "has_common_quarter",
                    "eligible",
                ]
            ].all(axis=1)
        ).sum()
    )
    selected_sample_mismatch = int(
        len(
            selected[
                ["window", "country", "series", "survey"]
            ].merge(
                countries[
                    ["window", "country", "series", "survey"]
                ],
                on=["window", "country", "series", "survey"],
                how="outer",
                indicator=True,
            ).query("_merge != 'both'")
        )
    )

    income_error_columns = [
        "income_reconstruction_error_0",
        "income_reconstruction_error_1",
        "max_abs_period_income_error",
    ]
    worker_error_columns = [
        "worker_reconstruction_error_0",
        "worker_reconstruction_error_1",
        "max_abs_period_worker_error",
    ]
    maximum_income_reconstruction_error = float(
        countries[income_error_columns].abs().to_numpy().max()
    )
    maximum_worker_reconstruction_error = float(
        countries[worker_error_columns].abs().to_numpy().max()
    )

    checks = {
        "duplicate_country_keys": duplicate_country_keys,
        "duplicate_group_keys": duplicate_group_keys,
        "duplicate_aggregate_keys": duplicate_aggregate_keys,
        "maximum_share_sum_error": share_sum_error,
        "maximum_education_group_sum_error": (
            education_group_sum_error
        ),
        "maximum_within_group_sum_error": within_group_sum_error,
        "maximum_country_identity_error": country_identity_error,
        "maximum_aggregate_identity_error": aggregate_identity_error,
        "selected_quality_failures": selected_quality_failures,
        "selected_sample_mismatch": selected_sample_mismatch,
        "maximum_income_reconstruction_error": (
            maximum_income_reconstruction_error
        ),
        "maximum_worker_reconstruction_error": (
            maximum_worker_reconstruction_error
        ),
        "finite_country_values": bool(
            np.isfinite(
                countries[
                    [
                        "mean_income_0_usd_2017_ppp",
                        "mean_income_1_usd_2017_ppp",
                        "education_component_usd_2017_ppp",
                        "within_income_component_usd_2017_ppp",
                    ]
                ].to_numpy()
            ).all()
        ),
        "positive_country_mean_incomes": bool(
            countries[
                [
                    "mean_income_0_usd_2017_ppp",
                    "mean_income_1_usd_2017_ppp",
                ]
            ]
            .gt(0)
            .all()
            .all()
        ),
        "positive_common_quarter_counts": bool(
            countries["n_common_quarters"].gt(0).all()
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
        and maximum_income_reconstruction_error
        <= MAX_INCOME_RECONSTRUCTION_ERROR
        and maximum_worker_reconstruction_error
        <= MAX_WORKER_RECONSTRUCTION_ERROR
        and checks["finite_country_values"]
        and checks["positive_country_mean_incomes"]
        and checks["positive_common_quarter_counts"]
    )
    summary = {
        "status": "PASS" if passed else "FAIL",
        "tolerance": TOLERANCE,
        "checks": checks,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
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
