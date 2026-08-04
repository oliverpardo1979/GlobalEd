"""Audit the LABLAC aggregates used for the education-remuneration decomposition."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "raw" / "world_bank_lablac"
KEYS = ["Country", "Period", "Series", "Survey"]
EDUCATION = [
    "Educational attainment - low",
    "Educational attainment - middle",
    "Educational attainment - high",
]


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    wages = pd.read_excel(DATA_DIR / "Wage-tableau.xlsx")
    workers = pd.read_excel(DATA_DIR / "Workers-tableau.xlsx")
    for frame in (wages, workers):
        frame.dropna(subset=["Value"], inplace=True)
        frame["Series"] = frame["Series"].astype("Int64")
    return wages, workers


def relative_error_summary(errors: pd.Series) -> dict[str, float | int]:
    absolute = errors.abs()
    return {
        "comparisons": int(errors.size),
        "median_absolute_relative_error": float(absolute.median()),
        "p90_absolute_relative_error": float(absolute.quantile(0.9)),
        "maximum_absolute_relative_error": float(absolute.max()),
    }


def audit() -> dict[str, object]:
    wages, workers = load_data()
    results: dict[str, object] = {
        "duplicate_wage_rows": int(
            wages.duplicated(KEYS + ["Indicator", "Category"], keep=False).sum()
        ),
        "duplicate_worker_rows": int(
            workers.duplicated(KEYS + ["Indicator", "Category"], keep=False).sum()
        ),
    }

    worker_rows = workers[
        (workers["Indicator"] == "Total Workers")
        & workers["Category"].isin(EDUCATION + ["Total"])
    ]
    worker_pivot = worker_rows.pivot(
        index=KEYS, columns="Category", values="Value"
    )
    worker_pivot["education_sum"] = worker_pivot[EDUCATION].sum(
        axis=1, min_count=len(EDUCATION)
    )
    worker_gap = (
        worker_pivot["education_sum"] - worker_pivot["Total"]
    ) / worker_pivot["Total"]
    results["worker_total_reconstruction"] = relative_error_summary(
        worker_gap.dropna()
    )

    wage_reconstruction: dict[str, object] = {}
    for indicator in ["Mean Monthly Labor Income", "Mean Hourly Wage"]:
        wage_rows = wages[
            (wages["Indicator"] == indicator)
            & wages["Category"].isin(EDUCATION + ["Total"])
        ]
        wage_pivot = wage_rows.pivot(
            index=KEYS, columns="Category", values="Value"
        )
        joined = wage_pivot.join(
            worker_pivot[EDUCATION],
            how="inner",
            lsuffix="_wage",
            rsuffix="_workers",
        )
        wage_columns = [f"{group}_wage" for group in EDUCATION]
        worker_columns = [f"{group}_workers" for group in EDUCATION]
        complete = joined.dropna(
            subset=wage_columns + worker_columns + ["Total"]
        )
        weighted = (
            complete[wage_columns].to_numpy()
            * complete[worker_columns].to_numpy()
        ).sum(axis=1) / complete[worker_columns].sum(axis=1)
        errors = pd.Series(
            (weighted - complete["Total"].to_numpy())
            / complete["Total"].to_numpy(),
            index=complete.index,
        )

        country_profiles: list[dict[str, object]] = []
        for country, country_errors in errors.groupby(level="Country"):
            periods = country_errors.index.get_level_values("Period")
            country_profiles.append(
                {
                    "country": country,
                    "first_period": str(min(periods)),
                    "last_period": str(max(periods)),
                    **relative_error_summary(country_errors),
                    "mean_signed_relative_error": float(country_errors.mean()),
                }
            )

        wage_reconstruction[indicator] = {
            **relative_error_summary(errors),
            "countries": country_profiles,
        }

    results["wage_total_reconstruction"] = wage_reconstruction
    return results


if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
