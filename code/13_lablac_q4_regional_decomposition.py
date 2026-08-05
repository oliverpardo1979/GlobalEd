"""Regional LABLAC decomposition for a common 2017-Q4--2022-Q4 window.

The script uses the same source-selection rule and country-level symmetric
decomposition as ``10_lablac_q4_country_decomposition.py``. It then aggregates
the 14 covered economies in three ways:

1. fixed employment weights: each economy's weight is proportional to its
   average number of workers across the two endpoints;
2. changing employment weights: endpoint-specific worker shares, with an
   additional between-economy composition component; and
3. equal economy weights.

All aggregates are exact accounting decompositions of synthetic mean monthly
labor income in 2017 PPP US dollars.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CODE_DIR = ROOT / "code"
OUTPUT_DIR = (
    ROOT / "data" / "processed" / "lablac_q4_regional_decomposition"
)
TABLE_DIR = ROOT / "tables"

COUNTRY_SCRIPT = CODE_DIR / "10_lablac_q4_country_decomposition.py"
START_YEAR = 2017
END_YEAR = 2022
YEARS_ELAPSED = END_YEAR - START_YEAR
EXPECTED_COUNTRIES = 14

METHOD_LABELS = {
    "fixed_employment_weights": "Fixed employment weights",
    "changing_employment_weights": "Observed employment weights",
    "equal_country_weights": "Equal weights by economy",
}


def load_country_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "lablac_q4_country_decomposition",
        COUNTRY_SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load {COUNTRY_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def latex_escape(value: object) -> str:
    text = str(value)
    replacements = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def format_rate(value: float) -> str:
    rounded = round(value, 1)
    if rounded == 0:
        rounded = 0.0
    return f"{rounded:.1f}"


def format_contribution(value: float) -> str:
    rounded = round(value, 2)
    if rounded == 0:
        rounded = 0.0
    return f"{rounded:.2f}"


def select_common_endpoints(
    candidates: pd.DataFrame,
    source_keys: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    eligible = candidates[
        candidates["complete"]
        & candidates["year"].isin([START_YEAR, END_YEAR])
    ].copy()
    coverage = (
        eligible.groupby("country")["year"]
        .nunique()
        .rename("endpoint_years")
    )
    covered_countries = coverage[coverage.eq(2)].index
    eligible = eligible[eligible["country"].isin(covered_countries)].copy()

    eligible["endpoint"] = np.where(
        eligible["year"].eq(START_YEAR),
        "initial",
        "final",
    )
    eligible = eligible.sort_values(
        [
            "country",
            "endpoint",
            "dashboard_cells_matched",
            "total_dashboard_gap",
            "published_total_workers",
            "series",
        ],
        ascending=[True, True, False, True, False, False],
    )
    selected = eligible.drop_duplicates(
        ["country", "endpoint"],
        keep="first",
    ).sort_values(["country", "year"])

    selected_keys = selected[source_keys + ["endpoint"]].assign(
        selected=True
    )
    audit = candidates[
        candidates["year"].isin([START_YEAR, END_YEAR])
    ].merge(
        selected_keys,
        on=source_keys,
        how="left",
        validate="one_to_one",
    )
    audit["selected"] = audit["selected"].fillna(False).astype(bool)

    if selected["country"].nunique() != EXPECTED_COUNTRIES:
        raise ValueError(
            "Expected "
            f"{EXPECTED_COUNTRIES} common-window economies, found "
            f"{selected['country'].nunique()}"
        )
    if not (
        selected.groupby("country")["endpoint"].nunique().eq(2).all()
    ):
        raise ValueError("Each economy must have two selected endpoints")
    return selected, audit


def aggregate_decompositions(
    countries: pd.DataFrame,
    annualized_growth,
    annualized_component_factor,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    data = countries.copy()
    data["midpoint_workers"] = (
        data["workers_0"] + data["workers_1"]
    ) / 2
    data["weight_0"] = data["workers_0"] / data["workers_0"].sum()
    data["weight_1"] = data["workers_1"] / data["workers_1"].sum()
    data["midpoint_employment_weight"] = (
        data["midpoint_workers"] / data["midpoint_workers"].sum()
    )
    data["equal_country_weight"] = 1 / len(data)

    rows: list[dict[str, object]] = []
    for method in [
        "fixed_employment_weights",
        "changing_employment_weights",
        "equal_country_weights",
    ]:
        if method == "fixed_employment_weights":
            weights = data["midpoint_employment_weight"]
            mean_0 = float(
                (weights * data["synthetic_income_0_usd_2017_ppp"]).sum()
            )
            mean_1 = float(
                (weights * data["synthetic_income_1_usd_2017_ppp"]).sum()
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
            weights = data["equal_country_weight"]
            mean_0 = float(
                (weights * data["synthetic_income_0_usd_2017_ppp"]).sum()
            )
            mean_1 = float(
                (weights * data["synthetic_income_1_usd_2017_ppp"]).sum()
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
            weight_0 = data["weight_0"]
            weight_1 = data["weight_1"]
            average_weight = (weight_0 + weight_1) / 2
            mean_0 = float(
                (
                    weight_0
                    * data["synthetic_income_0_usd_2017_ppp"]
                ).sum()
            )
            mean_1 = float(
                (
                    weight_1
                    * data["synthetic_income_1_usd_2017_ppp"]
                ).sum()
            )
            education = float(
                (
                    average_weight
                    * data["education_component_usd_2017_ppp"]
                ).sum()
            )
            within = float(
                (
                    average_weight
                    * data["within_income_component_usd_2017_ppp"]
                ).sum()
            )
            country_composition = float(
                (
                    (
                        (
                            data["synthetic_income_0_usd_2017_ppp"]
                            + data["synthetic_income_1_usd_2017_ppp"]
                        )
                        / 2
                    )
                    * (weight_1 - weight_0)
                ).sum()
            )

        change = mean_1 - mean_0
        residual = (
            change - education - within - country_composition
        )
        percent_change = 100 * change / mean_0
        annualized_total = annualized_growth(
            mean_0,
            mean_1,
            YEARS_ELAPSED,
        )
        factor = annualized_component_factor(
            percent_change,
            annualized_total,
            YEARS_ELAPSED,
        )
        education_percent = 100 * education / mean_0
        within_percent = 100 * within / mean_0
        country_percent = 100 * country_composition / mean_0
        rows.append(
            {
                "window": f"{START_YEAR}-{END_YEAR}",
                "aggregation": method,
                "aggregation_label": METHOD_LABELS[method],
                "n_countries": len(data),
                "mean_income_0_usd_2017_ppp": mean_0,
                "mean_income_1_usd_2017_ppp": mean_1,
                "change_usd_2017_ppp": change,
                "percent_change": percent_change,
                "annualized_growth_percent": annualized_total,
                "annualization_factor": factor,
                "education_component_usd_2017_ppp": education,
                "within_income_component_usd_2017_ppp": within,
                "country_composition_component_usd_2017_ppp": (
                    country_composition
                ),
                "residual_usd_2017_ppp": residual,
                "education_contribution_percent_initial": (
                    education_percent
                ),
                "within_income_contribution_percent_initial": (
                    within_percent
                ),
                "country_composition_contribution_percent_initial": (
                    country_percent
                ),
                "annualized_education_contribution_percentage_points": (
                    education_percent * factor
                ),
                "annualized_within_contribution_percentage_points": (
                    within_percent * factor
                ),
                "annualized_country_composition_percentage_points": (
                    country_percent * factor
                ),
            }
        )
    weight_columns = [
        "country",
        "workers_0",
        "workers_1",
        "weight_0",
        "weight_1",
        "midpoint_employment_weight",
        "equal_country_weight",
        "same_source",
        "start_series",
        "end_series",
        "start_survey",
        "end_survey",
    ]
    return pd.DataFrame(rows), data[weight_columns].sort_values("country")


def build_regional_descriptives(
    selected_cells: pd.DataFrame,
    education_order: list[str],
    education_labels: dict[str, str],
    annualized_growth,
) -> pd.DataFrame:
    cells = selected_cells.copy()
    cells["payroll"] = (
        cells["workers"] * cells["income_usd_2017_ppp"]
    )
    grouped = (
        cells.groupby(["endpoint", "education"], as_index=False)
        .agg(
            workers=("workers", "sum"),
            payroll=("payroll", "sum"),
        )
    )
    grouped["income_usd_2017_ppp"] = (
        grouped["payroll"] / grouped["workers"]
    )
    grouped["employment_share"] = grouped["workers"] / (
        grouped.groupby("endpoint")["workers"].transform("sum")
    )

    rows: list[dict[str, object]] = []
    for education in education_order:
        education_rows = grouped[
            grouped["education"].eq(education)
        ].set_index("endpoint")
        initial = education_rows.loc["initial"]
        final = education_rows.loc["final"]
        rows.append(
            {
                "education": education,
                "education_label": education_labels[education],
                "workers_0": float(initial["workers"]),
                "workers_1": float(final["workers"]),
                "employment_share_0": float(
                    initial["employment_share"]
                ),
                "employment_share_1": float(
                    final["employment_share"]
                ),
                "income_0_usd_2017_ppp": float(
                    initial["income_usd_2017_ppp"]
                ),
                "income_1_usd_2017_ppp": float(
                    final["income_usd_2017_ppp"]
                ),
                "annualized_income_growth_percent": annualized_growth(
                    float(initial["income_usd_2017_ppp"]),
                    float(final["income_usd_2017_ppp"]),
                    YEARS_ELAPSED,
                ),
            }
        )

    total_by_endpoint = (
        cells.groupby("endpoint", as_index=True)
        .agg(workers=("workers", "sum"), payroll=("payroll", "sum"))
    )
    total_by_endpoint["income_usd_2017_ppp"] = (
        total_by_endpoint["payroll"] / total_by_endpoint["workers"]
    )
    total_initial = total_by_endpoint.loc["initial"]
    total_final = total_by_endpoint.loc["final"]
    total = {
        "education": "Total",
        "education_label": "Total",
        "workers_0": float(total_initial["workers"]),
        "workers_1": float(total_final["workers"]),
        "employment_share_0": 1.0,
        "employment_share_1": 1.0,
        "income_0_usd_2017_ppp": float(
            total_initial["income_usd_2017_ppp"]
        ),
        "income_1_usd_2017_ppp": float(
            total_final["income_usd_2017_ppp"]
        ),
        "annualized_income_growth_percent": annualized_growth(
            float(total_initial["income_usd_2017_ppp"]),
            float(total_final["income_usd_2017_ppp"]),
            YEARS_ELAPSED,
        ),
    }
    return pd.DataFrame([total] + rows)


def format_descriptive_table(descriptives: pd.DataFrame) -> str:
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        (
            r"\caption{Common-window descriptive statistics for the "
            r"covered economies}"
        ),
        r"\label{tab:latam_regional_descriptives}",
        r"\small",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{lrrrrrrr}",
        r"\toprule",
        (
            r"Group & Workers 2017 & Workers 2022 & Share 2017 & "
            r"Share 2022 & Income 2017 & Income 2022 & Annual growth \\"
        ),
        (
            r"& \multicolumn{2}{c}{Millions} & "
            r"\multicolumn{2}{c}{Percent} & "
            r"\multicolumn{2}{c}{2017 PPP US dollars} & Percent \\"
        ),
        r"\midrule",
    ]
    for row in descriptives.itertuples(index=False):
        lines.append(
            f"{latex_escape(row.education_label)} & "
            f"{row.workers_0 / 1_000_000:.1f} & "
            f"{row.workers_1 / 1_000_000:.1f} & "
            f"{100 * row.employment_share_0:.1f} & "
            f"{100 * row.employment_share_1:.1f} & "
            f"{row.income_0_usd_2017_ppp:,.0f} & "
            f"{row.income_1_usd_2017_ppp:,.0f} & "
            f"{format_rate(row.annualized_income_growth_percent)} \\\\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"}",
            r"\begin{minipage}{0.98\textwidth}",
            r"\footnotesize",
            (
                r"\textit{Note:} The table pools the 14 covered economies "
                r"using their published worker counts. Income is mean monthly "
                r"labor income per employed person in 2017 PPP US dollars. "
                r"Annual growth is the compound annual rate between the "
                r"2017-Q4 and 2022-Q4 endpoints. Peru refers to Lima and "
                r"Callao."
            ),
            r"\end{minipage}",
            r"\end{table}",
            "",
        ]
    )
    return "\n".join(lines)


def format_decomposition_table(aggregates: pd.DataFrame) -> str:
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        (
            r"\caption{Aggregate annualized decomposition, "
            r"2017-Q4--2022-Q4}"
        ),
        r"\label{tab:latam_regional_decomposition}",
        r"\small",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{lrrrrrr}",
        r"\toprule",
        (
            r"Aggregation & Income 2017 & Income 2022 & Total growth & "
            r"Economy composition & Education & Within-group income \\"
        ),
        (
            r"& \multicolumn{2}{c}{2017 PPP US dollars} & "
            r"\multicolumn{4}{c}{Percentage points per year} \\"
        ),
        r"\midrule",
    ]
    for row in aggregates.itertuples(index=False):
        lines.append(
            f"{latex_escape(row.aggregation_label)} & "
            f"{row.mean_income_0_usd_2017_ppp:,.0f} & "
            f"{row.mean_income_1_usd_2017_ppp:,.0f} & "
            f"{format_contribution(row.annualized_growth_percent)} & "
            f"{format_contribution(row.annualized_country_composition_percentage_points)} & "
            f"{format_contribution(row.annualized_education_contribution_percentage_points)} & "
            f"{format_contribution(row.annualized_within_contribution_percentage_points)} \\\\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"}",
            r"\begin{minipage}{0.98\textwidth}",
            r"\footnotesize",
            (
                r"\textit{Note:} Fixed employment weights are proportional "
                r"to each economy's average number of workers across the two "
                r"endpoints and constitute the baseline. Observed employment "
                r"weights use each economy's endpoint-specific worker share "
                r"and therefore include an economy-composition component. "
                r"Equal weights describe the average economy. Components are "
                r"common-rescaling allocations and add to total compound "
                r"annual growth before rounding. Colombia, Ecuador, Paraguay, "
                r"and Uruguay cross a Tableau series or survey change."
            ),
            r"\end{minipage}",
            r"\end{table}",
            "",
        ]
    )
    return "\n".join(lines)


def validate_outputs(
    selected: pd.DataFrame,
    selected_cells: pd.DataFrame,
    countries: pd.DataFrame,
    aggregates: pd.DataFrame,
    descriptives: pd.DataFrame,
) -> dict[str, object]:
    aggregate_identity_error = (
        aggregates["residual_usd_2017_ppp"].abs().max()
    )
    annualized_identity_error = (
        aggregates["annualized_growth_percent"]
        - aggregates[
            "annualized_country_composition_percentage_points"
        ]
        - aggregates[
            "annualized_education_contribution_percentage_points"
        ]
        - aggregates[
            "annualized_within_contribution_percentage_points"
        ]
    ).abs().max()
    share_sums = descriptives[
        descriptives["education_label"].ne("Total")
    ][["employment_share_0", "employment_share_1"]].sum()
    changing = aggregates[
        aggregates["aggregation"].eq("changing_employment_weights")
    ].iloc[0]
    total = descriptives[
        descriptives["education_label"].eq("Total")
    ].iloc[0]
    source_changes = int((~countries["same_source"]).sum())
    checks = {
        "countries": int(countries["country"].nunique()),
        "selected_endpoints": int(len(selected)),
        "selected_cells": int(len(selected_cells)),
        "all_endpoints_q4": bool(
            selected["period"].str.endswith("-Q4").all()
        ),
        "endpoint_years": sorted(
            selected["year"].astype(int).unique().tolist()
        ),
        "three_education_cells_per_endpoint": bool(
            selected_cells.groupby(["country", "endpoint"])
            ["education"]
            .nunique()
            .eq(3)
            .all()
        ),
        "positive_incomes_and_workers": bool(
            selected_cells["income_usd_2017_ppp"].gt(0).all()
            and selected_cells["workers"].gt(0).all()
        ),
        "maximum_aggregate_identity_error": float(
            aggregate_identity_error
        ),
        "maximum_annualized_identity_error": float(
            annualized_identity_error
        ),
        "maximum_regional_share_sum_error": float(
            max(abs(share_sums["employment_share_0"] - 1), abs(
                share_sums["employment_share_1"] - 1
            ))
        ),
        "changing_weight_income_0_reconciliation_error": float(
            changing["mean_income_0_usd_2017_ppp"]
            - total["income_0_usd_2017_ppp"]
        ),
        "changing_weight_income_1_reconciliation_error": float(
            changing["mean_income_1_usd_2017_ppp"]
            - total["income_1_usd_2017_ppp"]
        ),
        "countries_with_source_change": source_changes,
    }
    tolerance = 1e-9
    passed = bool(
        checks["countries"] == EXPECTED_COUNTRIES
        and checks["selected_endpoints"] == 2 * EXPECTED_COUNTRIES
        and checks["selected_cells"] == 6 * EXPECTED_COUNTRIES
        and checks["all_endpoints_q4"]
        and checks["endpoint_years"] == [START_YEAR, END_YEAR]
        and checks["three_education_cells_per_endpoint"]
        and checks["positive_incomes_and_workers"]
        and checks["maximum_aggregate_identity_error"] <= tolerance
        and checks["maximum_annualized_identity_error"] <= tolerance
        and checks["maximum_regional_share_sum_error"] <= tolerance
        and abs(
            checks["changing_weight_income_0_reconciliation_error"]
        )
        <= tolerance
        and abs(
            checks["changing_weight_income_1_reconciliation_error"]
        )
        <= tolerance
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "tolerance": tolerance,
        "checks": checks,
    }


def main() -> None:
    country_module = load_country_module()
    cells, candidates, _ = country_module.build_source_candidates()
    selected, audit = select_common_endpoints(
        candidates,
        country_module.SOURCE_KEYS,
    )
    countries, groups, descriptives_country = (
        country_module.build_outputs(cells, selected)
    )
    selected_cells = cells.merge(
        selected[country_module.SOURCE_KEYS + ["endpoint"]],
        on=country_module.SOURCE_KEYS,
        how="inner",
        validate="many_to_one",
    )
    selected_cells["education_label"] = selected_cells[
        "education"
    ].map(country_module.EDUCATION_LABELS)

    aggregates, country_weights = aggregate_decompositions(
        countries,
        country_module.annualized_growth,
        country_module.annualized_component_factor,
    )
    regional_descriptives = build_regional_descriptives(
        selected_cells,
        country_module.EDUCATION,
        country_module.EDUCATION_LABELS,
        country_module.annualized_growth,
    )
    validation = validate_outputs(
        selected,
        selected_cells,
        countries,
        aggregates,
        regional_descriptives,
    )
    if validation["status"] != "PASS":
        raise ValueError(json.dumps(validation, indent=2))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    selected.to_csv(OUTPUT_DIR / "selected_endpoints.csv", index=False)
    audit.to_csv(OUTPUT_DIR / "source_selection_audit.csv", index=False)
    selected_cells.to_csv(
        OUTPUT_DIR / "selected_endpoint_cells.csv",
        index=False,
    )
    countries.to_csv(
        OUTPUT_DIR / "country_decompositions_2017_2022.csv",
        index=False,
    )
    groups.to_csv(
        OUTPUT_DIR / "country_education_components_2017_2022.csv",
        index=False,
    )
    descriptives_country.to_csv(
        OUTPUT_DIR / "country_endpoint_descriptives_2017_2022.csv",
        index=False,
    )
    country_weights.to_csv(
        OUTPUT_DIR / "country_weights.csv",
        index=False,
    )
    aggregates.to_csv(
        OUTPUT_DIR / "regional_decompositions.csv",
        index=False,
    )
    regional_descriptives.to_csv(
        OUTPUT_DIR / "regional_descriptives.csv",
        index=False,
    )
    with (OUTPUT_DIR / "validation_summary.json").open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(validation, handle, ensure_ascii=False, indent=2)

    (
        TABLE_DIR / "latam_regional_descriptives.tex"
    ).write_text(
        format_descriptive_table(regional_descriptives),
        encoding="utf-8",
    )
    (
        TABLE_DIR / "latam_regional_decomposition.tex"
    ).write_text(
        format_decomposition_table(aggregates),
        encoding="utf-8",
    )

    print(json.dumps(validation, ensure_ascii=False, indent=2))
    print()
    print(
        aggregates[
            [
                "aggregation_label",
                "mean_income_0_usd_2017_ppp",
                "mean_income_1_usd_2017_ppp",
                "annualized_growth_percent",
                "annualized_country_composition_percentage_points",
                "annualized_education_contribution_percentage_points",
                "annualized_within_contribution_percentage_points",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
