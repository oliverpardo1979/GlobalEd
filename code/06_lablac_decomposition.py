"""Build exact education/remuneration decompositions for Latin America.

The LABLAC source reports quarterly mean monthly labor income and worker
counts by educational attainment. Each comparison requires only the initial
and final year. Within those two years, the script uses the same observed
quarters for a country, survey, and series so that seasonality and survey
frequency are held fixed.

The outcome is a synthetic mean over three education groups. It is exactly
decomposable with the published worker counts, although it need not reproduce
LABLAC's published total because the income indicator is limited to workers
with coherent reported income.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "world_bank_lablac"
OUTPUT_DIR = ROOT / "data" / "processed" / "lablac_decomposition"
TABLE_DIR = ROOT / "tables"

WAGE_FILE = RAW_DIR / "Wage-tableau.xlsx"
WORKER_FILE = RAW_DIR / "Workers-tableau.xlsx"

WINDOWS = [
    (2016, 2019),
    (2016, 2023),
    (2019, 2023),
]

EDUCATION = [
    "Educational attainment - low",
    "Educational attainment - middle",
    "Educational attainment - high",
]

EDUCATION_LABELS = {
    "Educational attainment - low": "Low",
    "Educational attainment - middle": "Middle",
    "Educational attainment - high": "High",
}

MAX_INCOME_RECONSTRUCTION_ERROR = 0.05
MAX_WORKER_RECONSTRUCTION_ERROR = 0.03

SOURCE_KEYS = ["country", "series", "survey"]
PERIOD_KEYS = SOURCE_KEYS + ["period"]


def parse_period(frame: pd.DataFrame) -> pd.DataFrame:
    parsed = frame["period"].str.extract(r"^(\d{4})-Q([1-4])$")
    if parsed.isna().any().any():
        invalid = frame.loc[
            parsed.isna().any(axis=1), "period"
        ].drop_duplicates()
        raise ValueError(f"Unexpected LABLAC periods: {invalid.tolist()}")
    result = frame.copy()
    result["year"] = parsed[0].astype(int)
    result["quarter"] = parsed[1].astype(int)
    return result


def prepare_rows(
    frame: pd.DataFrame,
    indicator: str,
    categories: list[str],
    value_name: str,
) -> pd.DataFrame:
    rows = frame[
        frame["Indicator"].eq(indicator)
        & frame["Category"].isin(categories)
        & frame["Value"].notna()
    ][
        [
            "Country",
            "Period",
            "Series",
            "Survey",
            "Category",
            "Value",
        ]
    ].rename(
        columns={
            "Country": "country",
            "Period": "period",
            "Series": "series",
            "Survey": "survey",
            "Category": "education",
            "Value": value_name,
        }
    )
    rows["series"] = rows["series"].astype("Int64")
    return parse_period(rows)


def load_lablac_cells() -> tuple[pd.DataFrame, pd.DataFrame]:
    wages_raw = pd.read_excel(WAGE_FILE)
    workers_raw = pd.read_excel(WORKER_FILE)

    incomes = prepare_rows(
        wages_raw,
        "Mean Monthly Labor Income",
        EDUCATION,
        "income_usd_2017_ppp",
    )
    workers = prepare_rows(
        workers_raw,
        "Total Workers",
        EDUCATION,
        "workers",
    )

    cell_keys = PERIOD_KEYS + ["education"]
    duplicate_incomes = int(
        incomes.duplicated(cell_keys, keep=False).sum()
    )
    duplicate_workers = int(
        workers.duplicated(cell_keys, keep=False).sum()
    )
    if duplicate_incomes or duplicate_workers:
        raise ValueError(
            "Duplicate LABLAC education cells: "
            f"income={duplicate_incomes}, workers={duplicate_workers}"
        )

    cells = incomes.merge(
        workers[cell_keys + ["workers"]],
        on=cell_keys,
        how="inner",
        validate="one_to_one",
    )
    cells["payroll"] = (
        cells["income_usd_2017_ppp"] * cells["workers"]
    )
    cells["positive_cell"] = (
        cells["income_usd_2017_ppp"].gt(0)
        & cells["workers"].gt(0)
    )

    totals_income = prepare_rows(
        wages_raw,
        "Mean Monthly Labor Income",
        ["Total"],
        "published_total_income_usd_2017_ppp",
    ).drop(columns=["education"])
    totals_workers = prepare_rows(
        workers_raw,
        "Total Workers",
        ["Total"],
        "published_total_workers",
    ).drop(columns=["education"])

    period_quality = (
        cells.groupby(
            PERIOD_KEYS + ["year", "quarter"],
            as_index=False,
        )
        .agg(
            education_groups=("education", "nunique"),
            all_cells_positive=("positive_cell", "all"),
            stated_workers=("workers", "sum"),
            payroll=("payroll", "sum"),
        )
    )
    period_quality["synthetic_income_usd_2017_ppp"] = (
        period_quality["payroll"]
        / period_quality["stated_workers"]
    )
    period_quality = (
        period_quality.merge(
            totals_income[
                PERIOD_KEYS
                + ["published_total_income_usd_2017_ppp"]
            ],
            on=PERIOD_KEYS,
            how="left",
            validate="one_to_one",
        )
        .merge(
            totals_workers[
                PERIOD_KEYS + ["published_total_workers"]
            ],
            on=PERIOD_KEYS,
            how="left",
            validate="one_to_one",
        )
    )
    period_quality["income_reconstruction_error"] = (
        period_quality["synthetic_income_usd_2017_ppp"]
        - period_quality["published_total_income_usd_2017_ppp"]
    ) / period_quality["published_total_income_usd_2017_ppp"]
    period_quality["worker_reconstruction_error"] = (
        period_quality["stated_workers"]
        - period_quality["published_total_workers"]
    ) / period_quality["published_total_workers"]
    period_quality["clean_period"] = (
        period_quality["education_groups"].eq(len(EDUCATION))
        & period_quality["all_cells_positive"]
        & period_quality[
            "published_total_income_usd_2017_ppp"
        ].gt(0)
        & period_quality["published_total_workers"].gt(0)
        & period_quality["income_reconstruction_error"]
        .abs()
        .le(MAX_INCOME_RECONSTRUCTION_ERROR)
        & period_quality["worker_reconstruction_error"]
        .abs()
        .le(MAX_WORKER_RECONSTRUCTION_ERROR)
    )
    return cells, period_quality


def annualize_endpoint(
    cells: pd.DataFrame,
    quality: pd.DataFrame,
    start_year: int,
    end_year: int,
    common_quarters: list[int],
) -> tuple[pd.DataFrame, dict[int, dict[str, float]]]:
    endpoints = cells[
        cells["year"].isin([start_year, end_year])
        & cells["quarter"].isin(common_quarters)
    ].copy()
    annual = (
        endpoints.groupby(["year", "education"], as_index=False)
        .agg(
            payroll=("payroll", "sum"),
            worker_quarters=("workers", "sum"),
            workers=("workers", "mean"),
            observations=("quarter", "nunique"),
        )
    )
    annual["income_usd_2017_ppp"] = (
        annual["payroll"] / annual["worker_quarters"]
    )

    endpoint_quality = quality[
        quality["year"].isin([start_year, end_year])
        & quality["quarter"].isin(common_quarters)
    ].copy()
    endpoint_quality["published_payroll"] = (
        endpoint_quality["published_total_income_usd_2017_ppp"]
        * endpoint_quality["published_total_workers"]
    )
    published = (
        endpoint_quality.groupby("year", as_index=False)
        .agg(
            published_payroll=("published_payroll", "sum"),
            published_worker_quarters=(
                "published_total_workers",
                "sum",
            ),
            published_total_workers=(
                "published_total_workers",
                "mean",
            ),
            max_abs_period_income_error=(
                "income_reconstruction_error",
                lambda x: float(x.abs().max()),
            ),
            max_abs_period_worker_error=(
                "worker_reconstruction_error",
                lambda x: float(x.abs().max()),
            ),
        )
    )
    published["published_total_income_usd_2017_ppp"] = (
        published["published_payroll"]
        / published["published_worker_quarters"]
    )
    published_lookup = published.set_index("year")

    diagnostics: dict[int, dict[str, float]] = {}
    for year, year_data in annual.groupby("year"):
        synthetic_workers = float(year_data["workers"].sum())
        shares = year_data["workers"] / synthetic_workers
        synthetic_income = float(
            (shares * year_data["income_usd_2017_ppp"]).sum()
        )
        published_row = published_lookup.loc[year]
        published_income = float(
            published_row["published_total_income_usd_2017_ppp"]
        )
        published_workers = float(
            published_row["published_total_workers"]
        )
        diagnostics[int(year)] = {
            "synthetic_income_usd_2017_ppp": synthetic_income,
            "synthetic_workers": synthetic_workers,
            "published_total_income_usd_2017_ppp": published_income,
            "published_total_workers": published_workers,
            "annual_income_reconstruction_error": (
                synthetic_income - published_income
            )
            / published_income,
            "annual_worker_reconstruction_error": (
                synthetic_workers - published_workers
            )
            / published_workers,
            "max_abs_period_income_error": float(
                published_row["max_abs_period_income_error"]
            ),
            "max_abs_period_worker_error": float(
                published_row["max_abs_period_worker_error"]
            ),
        }
    return annual, diagnostics


def decompose_candidate(
    source_cells: pd.DataFrame,
    source_quality: pd.DataFrame,
    start_year: int,
    end_year: int,
    common_quarters: list[int],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    annual, diagnostics = annualize_endpoint(
        source_cells,
        source_quality,
        start_year,
        end_year,
        common_quarters,
    )
    expected_rows = 2 * len(EDUCATION)
    if (
        len(annual) != expected_rows
        or annual.groupby("year")["education"].nunique().min()
        != len(EDUCATION)
    ):
        raise ValueError(
            "Incomplete annualized endpoint groups for "
            f"{source_cells['country'].iloc[0]}, "
            f"{start_year}-{end_year}"
        )

    by_year = {
        int(year): data.set_index("education").reindex(EDUCATION)
        for year, data in annual.groupby("year")
    }
    start = by_year[start_year]
    end = by_year[end_year]
    workers_0 = float(start["workers"].sum())
    workers_1 = float(end["workers"].sum())
    shares_0 = start["workers"] / workers_0
    shares_1 = end["workers"] / workers_1
    income_0 = start["income_usd_2017_ppp"]
    income_1 = end["income_usd_2017_ppp"]
    mean_0 = float((shares_0 * income_0).sum())
    mean_1 = float((shares_1 * income_1).sum())
    education_component = float(
        (((income_0 + income_1) / 2) * (shares_1 - shares_0)).sum()
    )
    within_component = float(
        (((shares_0 + shares_1) / 2) * (income_1 - income_0)).sum()
    )
    change = mean_1 - mean_0

    country = source_cells["country"].iloc[0]
    series = int(source_cells["series"].iloc[0])
    survey = source_cells["survey"].iloc[0]
    window = f"{start_year}-{end_year}"
    country_row: dict[str, object] = {
        "window": window,
        "start_year": start_year,
        "end_year": end_year,
        "country": country,
        "series": series,
        "survey": survey,
        "common_quarters": ",".join(
            f"Q{quarter}" for quarter in common_quarters
        ),
        "n_common_quarters": len(common_quarters),
        "workers_0": workers_0,
        "workers_1": workers_1,
        "mean_income_0_usd_2017_ppp": mean_0,
        "mean_income_1_usd_2017_ppp": mean_1,
        "change_usd_2017_ppp": change,
        "education_component_usd_2017_ppp": education_component,
        "within_income_component_usd_2017_ppp": within_component,
        "residual_usd_2017_ppp": (
            change - education_component - within_component
        ),
        "percent_change": 100 * change / mean_0,
        "education_contribution_percent_initial": (
            100 * education_component / mean_0
        ),
        "within_income_contribution_percent_initial": (
            100 * within_component / mean_0
        ),
        "income_reconstruction_error_0": diagnostics[start_year][
            "annual_income_reconstruction_error"
        ],
        "income_reconstruction_error_1": diagnostics[end_year][
            "annual_income_reconstruction_error"
        ],
        "worker_reconstruction_error_0": diagnostics[start_year][
            "annual_worker_reconstruction_error"
        ],
        "worker_reconstruction_error_1": diagnostics[end_year][
            "annual_worker_reconstruction_error"
        ],
        "max_abs_period_income_error": max(
            diagnostics[start_year]["max_abs_period_income_error"],
            diagnostics[end_year]["max_abs_period_income_error"],
        ),
        "max_abs_period_worker_error": max(
            diagnostics[start_year]["max_abs_period_worker_error"],
            diagnostics[end_year]["max_abs_period_worker_error"],
        ),
    }

    group_rows: list[dict[str, object]] = []
    for education in EDUCATION:
        education_group_component = float(
            ((income_0.loc[education] + income_1.loc[education]) / 2)
            * (shares_1.loc[education] - shares_0.loc[education])
        )
        within_group_component = float(
            ((shares_0.loc[education] + shares_1.loc[education]) / 2)
            * (income_1.loc[education] - income_0.loc[education])
        )
        group_rows.append(
            {
                "window": window,
                "start_year": start_year,
                "end_year": end_year,
                "country": country,
                "series": series,
                "survey": survey,
                "education": education,
                "education_label": EDUCATION_LABELS[education],
                "common_quarters": country_row["common_quarters"],
                "share_0": float(shares_0.loc[education]),
                "share_1": float(shares_1.loc[education]),
                "income_0_usd_2017_ppp": float(
                    income_0.loc[education]
                ),
                "income_1_usd_2017_ppp": float(
                    income_1.loc[education]
                ),
                "education_component_usd_2017_ppp": (
                    education_group_component
                ),
                "within_income_component_usd_2017_ppp": (
                    within_group_component
                ),
            }
        )
    return country_row, group_rows


def build_endpoint_pairs(
    cells: pd.DataFrame,
    quality: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    audit_rows: list[dict[str, object]] = []
    candidate_rows: list[dict[str, object]] = []
    candidate_group_rows: list[dict[str, object]] = []

    for start_year, end_year in WINDOWS:
        for source_key, source_cells in cells.groupby(
            SOURCE_KEYS, sort=False
        ):
            country, series, survey = source_key
            source_quality = quality[
                quality["country"].eq(country)
                & quality["series"].eq(series)
                & quality["survey"].eq(survey)
            ]
            start_quarters = set(
                source_quality.loc[
                    source_quality["year"].eq(start_year),
                    "quarter",
                ].astype(int)
            )
            end_quarters = set(
                source_quality.loc[
                    source_quality["year"].eq(end_year),
                    "quarter",
                ].astype(int)
            )
            common_quarters = sorted(start_quarters & end_quarters)
            clean_start_quarters = set(
                source_quality.loc[
                    source_quality["year"].eq(start_year)
                    & source_quality["clean_period"],
                    "quarter",
                ].astype(int)
            )
            clean_end_quarters = set(
                source_quality.loc[
                    source_quality["year"].eq(end_year)
                    & source_quality["clean_period"],
                    "quarter",
                ].astype(int)
            )
            clean_common_quarters = sorted(
                clean_start_quarters & clean_end_quarters
            )
            both_endpoint_years = bool(
                start_quarters and end_quarters
            )
            has_common_quarter = bool(common_quarters)
            eligible = bool(clean_common_quarters)

            audit_rows.append(
                {
                    "window": f"{start_year}-{end_year}",
                    "start_year": start_year,
                    "end_year": end_year,
                    "country": country,
                    "series": int(series),
                    "survey": survey,
                    "both_endpoint_years": both_endpoint_years,
                    "has_common_quarter": has_common_quarter,
                    "common_quarters": ",".join(
                        f"Q{quarter}" for quarter in common_quarters
                    ),
                    "n_common_quarters": len(common_quarters),
                    "clean_common_quarters": ",".join(
                        f"Q{quarter}"
                        for quarter in clean_common_quarters
                    ),
                    "n_clean_common_quarters": len(
                        clean_common_quarters
                    ),
                    "eligible": eligible,
                }
            )
            if not eligible:
                continue

            country_row, group_rows = decompose_candidate(
                source_cells,
                source_quality,
                start_year,
                end_year,
                clean_common_quarters,
            )
            candidate_rows.append(country_row)
            candidate_group_rows.extend(group_rows)

    audit = pd.DataFrame(audit_rows)
    candidates = pd.DataFrame(candidate_rows)
    candidate_groups = pd.DataFrame(candidate_group_rows)
    candidates["midpoint_workers"] = (
        candidates["workers_0"] + candidates["workers_1"]
    ) / 2
    candidates = candidates.sort_values(
        [
            "window",
            "country",
            "n_common_quarters",
            "midpoint_workers",
            "series",
        ],
        ascending=[True, True, False, False, True],
    )
    selected_keys = candidates.drop_duplicates(
        ["window", "country"]
    )[["window", "country", "series", "survey"]].assign(selected=True)
    audit = audit.merge(
        selected_keys,
        on=["window", "country", "series", "survey"],
        how="left",
        validate="one_to_one",
    )
    audit["selected"] = audit["selected"].fillna(False).astype(bool)
    countries = candidates.merge(
        selected_keys,
        on=["window", "country", "series", "survey"],
        how="inner",
        validate="one_to_one",
    ).drop(columns=["selected"])
    groups = candidate_groups.merge(
        selected_keys,
        on=["window", "country", "series", "survey"],
        how="inner",
        validate="many_to_one",
    ).drop(columns=["selected"])
    return audit, countries, groups


def aggregate_decompositions(countries: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for window, data in countries.groupby("window", sort=False):
        n_countries = len(data)
        for method in [
            "fixed_employment_weights",
            "equal_country_weights",
            "changing_employment_weights",
        ]:
            if method == "fixed_employment_weights":
                weights = data["midpoint_workers"]
                weights = weights / weights.sum()
                mean_0 = float(
                    (weights * data["mean_income_0_usd_2017_ppp"]).sum()
                )
                mean_1 = float(
                    (weights * data["mean_income_1_usd_2017_ppp"]).sum()
                )
                education = float(
                    (
                        weights
                        * data["education_component_usd_2017_ppp"]
                    ).sum()
                )
                within = float(
                    (
                        weights
                        * data["within_income_component_usd_2017_ppp"]
                    ).sum()
                )
                country_composition = 0.0
            elif method == "equal_country_weights":
                weights = pd.Series(
                    1 / n_countries, index=data.index
                )
                mean_0 = float(
                    (weights * data["mean_income_0_usd_2017_ppp"]).sum()
                )
                mean_1 = float(
                    (weights * data["mean_income_1_usd_2017_ppp"]).sum()
                )
                education = float(
                    (
                        weights
                        * data["education_component_usd_2017_ppp"]
                    ).sum()
                )
                within = float(
                    (
                        weights
                        * data["within_income_component_usd_2017_ppp"]
                    ).sum()
                )
                country_composition = 0.0
            else:
                weights_0 = (
                    data["workers_0"] / data["workers_0"].sum()
                )
                weights_1 = (
                    data["workers_1"] / data["workers_1"].sum()
                )
                mean_0 = float(
                    (
                        weights_0
                        * data["mean_income_0_usd_2017_ppp"]
                    ).sum()
                )
                mean_1 = float(
                    (
                        weights_1
                        * data["mean_income_1_usd_2017_ppp"]
                    ).sum()
                )
                average_weights = (weights_0 + weights_1) / 2
                education = float(
                    (
                        average_weights
                        * data["education_component_usd_2017_ppp"]
                    ).sum()
                )
                within = float(
                    (
                        average_weights
                        * data["within_income_component_usd_2017_ppp"]
                    ).sum()
                )
                country_composition = float(
                    (
                        (
                            (
                                data["mean_income_0_usd_2017_ppp"]
                                + data["mean_income_1_usd_2017_ppp"]
                            )
                            / 2
                        )
                        * (weights_1 - weights_0)
                    ).sum()
                )

            change = mean_1 - mean_0
            residual = (
                change
                - education
                - within
                - country_composition
            )
            rows.append(
                {
                    "window": window,
                    "aggregation": method,
                    "n_countries": n_countries,
                    "mean_income_0_usd_2017_ppp": mean_0,
                    "mean_income_1_usd_2017_ppp": mean_1,
                    "change_usd_2017_ppp": change,
                    "education_component_usd_2017_ppp": education,
                    "within_income_component_usd_2017_ppp": within,
                    "country_composition_component_usd_2017_ppp": (
                        country_composition
                    ),
                    "residual_usd_2017_ppp": residual,
                    "percent_change": 100 * change / mean_0,
                    "education_contribution_percent_initial": (
                        100 * education / mean_0
                    ),
                    "within_income_contribution_percent_initial": (
                        100 * within / mean_0
                    ),
                    "country_composition_contribution_percent_initial": (
                        100 * country_composition / mean_0
                    ),
                }
            )
    return pd.DataFrame(rows)


def build_coverage_summary(audit: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for window, data in audit.groupby("window", sort=False):
        rows.append(
            {
                "window": window,
                "country_source_series": len(data),
                "sources_with_both_endpoint_years": int(
                    data["both_endpoint_years"].sum()
                ),
                "sources_with_common_quarter": int(
                    data["has_common_quarter"].sum()
                ),
                "sources_with_clean_common_quarter": int(
                    data["eligible"].sum()
                ),
                "selected_countries": int(data["selected"].sum()),
            }
        )
    return pd.DataFrame(rows)


def format_table(aggregates: pd.DataFrame) -> str:
    baseline = aggregates[
        aggregates["aggregation"].eq("fixed_employment_weights")
    ]
    rows = []
    for row in baseline.itertuples():
        rows.append(
            " & ".join(
                [
                    row.window.replace("-", "--"),
                    str(row.n_countries),
                    f"{row.percent_change:.1f}",
                    (
                        f"{row.education_contribution_percent_initial:.1f}"
                    ),
                    (
                        f"{row.within_income_contribution_percent_initial:.1f}"
                    ),
                ]
            )
            + r" \\"
        )
    body = "\n".join(rows)
    return rf"""\begin{{table}}[htbp]
\centering
\caption{{Baseline decomposition of real monthly labor-income growth}}
\label{{tab:latam_sample_decomposition}}
\begin{{tabular}}{{lrrrr}}
\toprule
Window & Economies & Total change & Education & Within-group income \\
& & \multicolumn{{3}}{{c}}{{Percent of initial synthetic mean income}} \\
\midrule
{body}
\bottomrule
\end{{tabular}}
\begin{{minipage}}{{0.96\textwidth}}
\textit{{Notes:}} Labor income is measured in 2017 purchasing-power-parity
dollars. Each comparison uses only the initial and final year and retains the
same observed quarters, survey, and series at both endpoints. The synthetic
mean weights the three education-group means with LABLAC's worker counts.
Economy weights are fixed at each economy's average number of workers at the
two endpoints. Total change equals the education and within-group income
contributions before rounding.
\end{{minipage}}
\end{{table}}
"""


def main() -> None:
    cells, quality = load_lablac_cells()
    audit, countries, groups = build_endpoint_pairs(cells, quality)
    aggregates = aggregate_decompositions(countries)
    coverage = build_coverage_summary(audit)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    audit.to_csv(OUTPUT_DIR / "window_source_audit.csv", index=False)
    coverage.to_csv(OUTPUT_DIR / "window_coverage_summary.csv", index=False)
    countries.to_csv(
        OUTPUT_DIR / "country_decompositions.csv", index=False
    )
    groups.to_csv(
        OUTPUT_DIR / "country_education_contributions.csv",
        index=False,
    )
    aggregates.to_csv(
        OUTPUT_DIR / "aggregate_decompositions.csv", index=False
    )
    (TABLE_DIR / "latam_sample_decomposition.tex").write_text(
        format_table(aggregates), encoding="utf-8"
    )

    summary = {
        "outcome": "synthetic_mean_monthly_labor_income",
        "unit": "2017 PPP dollars",
        "quality_thresholds": {
            "maximum_absolute_income_reconstruction_error": (
                MAX_INCOME_RECONSTRUCTION_ERROR
            ),
            "maximum_absolute_worker_reconstruction_error": (
                MAX_WORKER_RECONSTRUCTION_ERROR
            ),
        },
        "windows": coverage.to_dict("records"),
        "maximum_absolute_country_residual": float(
            countries["residual_usd_2017_ppp"].abs().max()
        ),
        "maximum_absolute_aggregate_residual": float(
            aggregates["residual_usd_2017_ppp"].abs().max()
        ),
    }
    with (OUTPUT_DIR / "decomposition_summary.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print()
    print(
        aggregates[
            [
                "window",
                "aggregation",
                "n_countries",
                "percent_change",
                "education_contribution_percent_initial",
                "within_income_contribution_percent_initial",
                "country_composition_contribution_percent_initial",
                "residual_usd_2017_ppp",
            ]
        ].to_string(index=False)
    )
    print()
    print("Selected country pairs")
    print(
        countries[
            [
                "window",
                "country",
                "series",
                "survey",
                "common_quarters",
                "percent_change",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
