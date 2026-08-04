"""Country-level LABLAC decomposition using Q4 endpoint observations.

For each country, the script selects the oldest and newest fourth-quarter
observation with complete education-group income and worker-count cells. When
more than one LABLAC survey series is available in an endpoint, it selects
the complete source that most closely reproduces the values displayed by the
Equity Lab Tableau workbook, with total workers as a secondary tie-breaker.

The exactly decomposed outcome is the synthetic mean monthly labor income:

    y_t = sum_e s_et * r_et,

where r_et is mean income in education group e and s_et is that group's share
of published workers. The published total income is retained as a diagnostic
because its estimation sample need not match the published worker counts.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "world_bank_lablac"
OUTPUT_DIR = ROOT / "data" / "processed" / "lablac_q4_decomposition"
TABLE_DIR = ROOT / "tables"

WAGE_FILE = RAW_DIR / "Wage-tableau.xlsx"
WORKER_FILE = RAW_DIR / "Workers-tableau.xlsx"

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
SOURCE_KEYS = ["country", "period", "year", "series", "survey"]
CELL_KEYS = SOURCE_KEYS + ["education"]


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


def parse_q4(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame[frame["Period"].str.endswith("-Q4", na=False)].copy()
    parsed = result["Period"].str.extract(r"^(\d{4})-Q4$")
    if parsed.isna().any().any():
        invalid = result.loc[parsed.isna().any(axis=1), "Period"].unique()
        raise ValueError(f"Unexpected Q4 labels: {invalid.tolist()}")
    result["year"] = parsed[0].astype(int)
    return result


def prepare_rows(
    frame: pd.DataFrame,
    indicator: str,
    categories: list[str],
    value_name: str,
) -> pd.DataFrame:
    rows = parse_q4(
        frame[
            frame["Indicator"].eq(indicator)
            & frame["Category"].isin(categories)
            & frame["Value"].notna()
        ]
    )
    rows = rows[
        [
            "Country",
            "Period",
            "Series",
            "Survey",
            "Category",
            "Value",
            "year",
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
    duplicates = int(rows.duplicated(CELL_KEYS, keep=False).sum())
    if duplicates:
        raise ValueError(
            f"Duplicate cells for {indicator}: {duplicates}"
        )
    return rows


def build_dashboard_reference(
    wages_raw: pd.DataFrame,
) -> pd.DataFrame:
    rows = prepare_rows(
        wages_raw,
        "Mean Monthly Labor Income",
        EDUCATION + ["Total"],
        "dashboard_income",
    )
    return (
        rows.groupby(
            ["country", "period", "year", "education"],
            as_index=False,
        )["dashboard_income"]
        .max()
    )


def build_source_candidates() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
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
    cells = incomes.merge(
        workers[CELL_KEYS + ["workers"]],
        on=CELL_KEYS,
        how="inner",
        validate="one_to_one",
    )
    cells["payroll"] = (
        cells["income_usd_2017_ppp"] * cells["workers"]
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

    candidates = (
        cells.groupby(SOURCE_KEYS, as_index=False)
        .agg(
            education_groups=("education", "nunique"),
            positive_incomes=("income_usd_2017_ppp", lambda x: x.gt(0).all()),
            positive_workers=("workers", lambda x: x.gt(0).all()),
            stated_workers=("workers", "sum"),
            payroll=("payroll", "sum"),
        )
        .merge(
            totals_income[
                SOURCE_KEYS
                + ["published_total_income_usd_2017_ppp"]
            ],
            on=SOURCE_KEYS,
            how="left",
            validate="one_to_one",
        )
        .merge(
            totals_workers[
                SOURCE_KEYS + ["published_total_workers"]
            ],
            on=SOURCE_KEYS,
            how="left",
            validate="one_to_one",
        )
    )
    candidates["synthetic_income_usd_2017_ppp"] = (
        candidates["payroll"] / candidates["stated_workers"]
    )
    candidates["income_reconstruction_error"] = (
        candidates["synthetic_income_usd_2017_ppp"]
        - candidates["published_total_income_usd_2017_ppp"]
    ) / candidates["published_total_income_usd_2017_ppp"]
    candidates["worker_reconstruction_error"] = (
        candidates["stated_workers"]
        - candidates["published_total_workers"]
    ) / candidates["published_total_workers"]
    candidates["complete"] = (
        candidates["education_groups"].eq(len(EDUCATION))
        & candidates["positive_incomes"]
        & candidates["positive_workers"]
        & candidates["published_total_income_usd_2017_ppp"].gt(0)
        & candidates["published_total_workers"].gt(0)
    )

    dashboard = build_dashboard_reference(wages_raw)
    dashboard_groups = dashboard[
        dashboard["education"].isin(EDUCATION)
    ]
    score = cells.merge(
        dashboard_groups,
        on=["country", "period", "year", "education"],
        how="left",
        validate="many_to_one",
    )
    score["absolute_dashboard_gap"] = (
        score["income_usd_2017_ppp"] - score["dashboard_income"]
    ).abs()
    source_score = (
        score.groupby(SOURCE_KEYS, as_index=False)
        .agg(
            dashboard_cells_matched=(
                "absolute_dashboard_gap",
                lambda x: int(x.eq(0).sum()),
            ),
            maximum_dashboard_gap=("absolute_dashboard_gap", "max"),
            total_dashboard_gap=("absolute_dashboard_gap", "sum"),
        )
    )
    candidates = candidates.merge(
        source_score,
        on=SOURCE_KEYS,
        how="left",
        validate="one_to_one",
    )
    return cells, candidates, dashboard


def select_endpoints(
    candidates: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    eligible = candidates[candidates["complete"]].copy()
    year_bounds = (
        eligible.groupby("country", as_index=False)
        .agg(start_year=("year", "min"), end_year=("year", "max"))
    )
    endpoints = eligible.merge(
        year_bounds,
        on="country",
        how="inner",
        validate="many_to_one",
    )
    endpoints = endpoints[
        endpoints["year"].eq(endpoints["start_year"])
        | endpoints["year"].eq(endpoints["end_year"])
    ].copy()
    endpoints["endpoint"] = np.where(
        endpoints["year"].eq(endpoints["start_year"]),
        "initial",
        "final",
    )
    endpoints = endpoints.sort_values(
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
    selected = endpoints.drop_duplicates(
        ["country", "endpoint"],
        keep="first",
    ).copy()
    selected_keys = selected[
        SOURCE_KEYS + ["endpoint"]
    ].assign(selected=True)
    audit = candidates.merge(
        selected_keys,
        on=SOURCE_KEYS,
        how="left",
        validate="one_to_one",
    )
    audit["selected"] = audit["selected"].fillna(False).astype(bool)
    selected = selected.sort_values(["country", "year"])
    counts = selected.groupby("country")["endpoint"].nunique()
    invalid = counts[counts.ne(2)]
    if len(invalid):
        raise ValueError(
            f"Countries without two selected endpoints: {invalid.to_dict()}"
        )
    return selected, audit


def build_outputs(
    cells: pd.DataFrame,
    selected: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    selected_cells = cells.merge(
        selected[SOURCE_KEYS + ["endpoint"]],
        on=SOURCE_KEYS,
        how="inner",
        validate="many_to_one",
    )
    selected_cells["education_label"] = selected_cells[
        "education"
    ].map(EDUCATION_LABELS)
    selected_cells["share"] = selected_cells["workers"] / (
        selected_cells.groupby(["country", "endpoint"])["workers"]
        .transform("sum")
    )

    country_rows: list[dict[str, object]] = []
    group_rows: list[dict[str, object]] = []
    descriptive_rows: list[dict[str, object]] = []

    for country, country_selected in selected.groupby(
        "country", sort=True
    ):
        source_by_endpoint = country_selected.set_index("endpoint")
        country_cells = selected_cells[
            selected_cells["country"].eq(country)
        ]
        initial = (
            country_cells[country_cells["endpoint"].eq("initial")]
            .set_index("education")
            .reindex(EDUCATION)
        )
        final = (
            country_cells[country_cells["endpoint"].eq("final")]
            .set_index("education")
            .reindex(EDUCATION)
        )
        if initial.isna().any().any() or final.isna().any().any():
            raise ValueError(f"Incomplete selected cells for {country}")

        s0 = initial["share"]
        s1 = final["share"]
        r0 = initial["income_usd_2017_ppp"]
        r1 = final["income_usd_2017_ppp"]
        mean0 = float((s0 * r0).sum())
        mean1 = float((s1 * r1).sum())
        change = mean1 - mean0
        education_component = float(
            (((r0 + r1) / 2) * (s1 - s0)).sum()
        )
        within_component = float(
            (((s0 + s1) / 2) * (r1 - r0)).sum()
        )

        source0 = source_by_endpoint.loc["initial"]
        source1 = source_by_endpoint.loc["final"]
        start_year = int(source0["year"])
        end_year = int(source1["year"])
        same_source = bool(
            source0["series"] == source1["series"]
            and source0["survey"] == source1["survey"]
        )
        row: dict[str, object] = {
            "country": country,
            "start_year": start_year,
            "end_year": end_year,
            "start_period": source0["period"],
            "end_period": source1["period"],
            "start_series": int(source0["series"]),
            "end_series": int(source1["series"]),
            "start_survey": source0["survey"],
            "end_survey": source1["survey"],
            "same_source": same_source,
            "workers_0": float(initial["workers"].sum()),
            "workers_1": float(final["workers"].sum()),
            "published_total_workers_0": float(
                source0["published_total_workers"]
            ),
            "published_total_workers_1": float(
                source1["published_total_workers"]
            ),
            "published_total_income_0_usd_2017_ppp": float(
                source0["published_total_income_usd_2017_ppp"]
            ),
            "published_total_income_1_usd_2017_ppp": float(
                source1["published_total_income_usd_2017_ppp"]
            ),
            "synthetic_income_0_usd_2017_ppp": mean0,
            "synthetic_income_1_usd_2017_ppp": mean1,
            "income_reconstruction_error_0": float(
                source0["income_reconstruction_error"]
            ),
            "income_reconstruction_error_1": float(
                source1["income_reconstruction_error"]
            ),
            "worker_reconstruction_error_0": float(
                source0["worker_reconstruction_error"]
            ),
            "worker_reconstruction_error_1": float(
                source1["worker_reconstruction_error"]
            ),
            "change_usd_2017_ppp": change,
            "percent_change": 100 * change / mean0,
            "education_component_usd_2017_ppp": education_component,
            "within_income_component_usd_2017_ppp": within_component,
            "education_contribution_percent_initial": (
                100 * education_component / mean0
            ),
            "within_income_contribution_percent_initial": (
                100 * within_component / mean0
            ),
            "residual_usd_2017_ppp": (
                change - education_component - within_component
            ),
        }
        for education in EDUCATION:
            label = EDUCATION_LABELS[education].lower()
            row[f"share_{label}_0"] = float(s0.loc[education])
            row[f"share_{label}_1"] = float(s1.loc[education])
            row[f"income_{label}_0_usd_2017_ppp"] = float(
                r0.loc[education]
            )
            row[f"income_{label}_1_usd_2017_ppp"] = float(
                r1.loc[education]
            )
            education_group_component = float(
                ((r0.loc[education] + r1.loc[education]) / 2)
                * (s1.loc[education] - s0.loc[education])
            )
            within_group_component = float(
                ((s0.loc[education] + s1.loc[education]) / 2)
                * (r1.loc[education] - r0.loc[education])
            )
            group_rows.append(
                {
                    "country": country,
                    "start_year": start_year,
                    "end_year": end_year,
                    "education": education,
                    "education_label": EDUCATION_LABELS[education],
                    "share_0": float(s0.loc[education]),
                    "share_1": float(s1.loc[education]),
                    "income_0_usd_2017_ppp": float(
                        r0.loc[education]
                    ),
                    "income_1_usd_2017_ppp": float(
                        r1.loc[education]
                    ),
                    "education_component_usd_2017_ppp": (
                        education_group_component
                    ),
                    "within_income_component_usd_2017_ppp": (
                        within_group_component
                    ),
                }
            )
            descriptive_rows.extend(
                [
                    {
                        "country": country,
                        "year": start_year,
                        "endpoint": "initial",
                        "education": education,
                        "education_label": EDUCATION_LABELS[education],
                        "share": float(s0.loc[education]),
                        "income_usd_2017_ppp": float(
                            r0.loc[education]
                        ),
                    },
                    {
                        "country": country,
                        "year": end_year,
                        "endpoint": "final",
                        "education": education,
                        "education_label": EDUCATION_LABELS[education],
                        "share": float(s1.loc[education]),
                        "income_usd_2017_ppp": float(
                            r1.loc[education]
                        ),
                    },
                ]
            )
        country_rows.append(row)

    countries = pd.DataFrame(country_rows).sort_values("country")
    groups = pd.DataFrame(group_rows).sort_values(
        ["country", "education"]
    )
    descriptives = pd.DataFrame(descriptive_rows).sort_values(
        ["country", "year", "education"]
    )
    return countries, groups, descriptives


def format_income_table(countries: pd.DataFrame) -> str:
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{Endpoint coverage and monthly labor income}",
        r"\label{tab:latam_country_income_descriptives}",
        r"\small",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{lrrrrrr}",
        r"\toprule",
        (
            r"Economy & Initial & Final & Published initial & "
            r"Published final & Synthetic initial & Synthetic final \\"
        ),
        r"\midrule",
    ]
    for row in countries.itertuples(index=False):
        lines.append(
            f"{latex_escape(row.country)} & "
            f"{row.start_year} & {row.end_year} & "
            f"{row.published_total_income_0_usd_2017_ppp:,.0f} & "
            f"{row.published_total_income_1_usd_2017_ppp:,.0f} & "
            f"{row.synthetic_income_0_usd_2017_ppp:,.0f} & "
            f"{row.synthetic_income_1_usd_2017_ppp:,.0f} \\\\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"}",
            r"\begin{minipage}{0.98\textwidth}",
            r"\footnotesize",
            (
                r"\textit{Note:} All observations are fourth-quarter "
                r"values measured in 2017 PPP US dollars per employed person "
                r"per month; they are not current US dollars or local currency. "
                r"Published income is LABLAC's reported total. Synthetic income "
                r"weights the three "
                r"education-group means with the published number of "
                r"workers in each group."
            ),
            r"\end{minipage}",
            r"\end{table}",
            "",
        ]
    )
    return "\n".join(lines)


def format_composition_table(countries: pd.DataFrame) -> str:
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{Composition of employment by educational attainment}",
        r"\label{tab:latam_country_education_shares}",
        r"\small",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{lrrrrrr}",
        r"\toprule",
        (
            r"Economy & Low initial & Low final & Middle initial & "
            r"Middle final & High initial & High final \\"
        ),
        r"\midrule",
    ]
    for row in countries.itertuples(index=False):
        lines.append(
            f"{latex_escape(row.country)} & "
            f"{100 * row.share_low_0:.1f} & "
            f"{100 * row.share_low_1:.1f} & "
            f"{100 * row.share_middle_0:.1f} & "
            f"{100 * row.share_middle_1:.1f} & "
            f"{100 * row.share_high_0:.1f} & "
            f"{100 * row.share_high_1:.1f} \\\\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"}",
            r"\begin{minipage}{0.98\textwidth}",
            r"\footnotesize",
            (
                r"\textit{Note:} Percent of employed workers in each "
                r"education group. Initial and final refer to the years "
                r"reported in Table~\ref{tab:latam_country_income_descriptives}."
            ),
            r"\end{minipage}",
            r"\end{table}",
            "",
        ]
    )
    return "\n".join(lines)


def format_group_income_table(countries: pd.DataFrame) -> str:
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{Monthly labor income by educational attainment}",
        r"\label{tab:latam_country_education_incomes}",
        r"\small",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{lrrrrrr}",
        r"\toprule",
        (
            r"Economy & Low initial & Low final & Middle initial & "
            r"Middle final & High initial & High final \\"
        ),
        r"\midrule",
    ]
    for row in countries.itertuples(index=False):
        lines.append(
            f"{latex_escape(row.country)} & "
            f"{row.income_low_0_usd_2017_ppp:,.0f} & "
            f"{row.income_low_1_usd_2017_ppp:,.0f} & "
            f"{row.income_middle_0_usd_2017_ppp:,.0f} & "
            f"{row.income_middle_1_usd_2017_ppp:,.0f} & "
            f"{row.income_high_0_usd_2017_ppp:,.0f} & "
            f"{row.income_high_1_usd_2017_ppp:,.0f} \\\\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"}",
            r"\begin{minipage}{0.98\textwidth}",
            r"\footnotesize",
            (
                r"\textit{Note:} Mean monthly labor income is measured in "
                r"2017 PPP US dollars per employed person per month; values "
                r"are not current US dollars or local currency. All observations "
                r"correspond to the fourth quarter."
            ),
            r"\end{minipage}",
            r"\end{table}",
            "",
        ]
    )
    return "\n".join(lines)


def format_decomposition_table(countries: pd.DataFrame) -> str:
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{Country-level decomposition of synthetic labor income}",
        r"\label{tab:latam_country_decomposition}",
        r"\small",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{lrrrrrr}",
        r"\toprule",
        (
            r"Economy & Initial & Final & Total change & Education & "
            r"Within groups & Same source \\"
        ),
        r"\midrule",
    ]
    for row in countries.itertuples(index=False):
        same_source = "Yes" if row.same_source else "No"
        lines.append(
            f"{latex_escape(row.country)} & "
            f"{row.start_year} & {row.end_year} & "
            f"{row.percent_change:.1f} & "
            f"{row.education_contribution_percent_initial:.1f} & "
            f"{row.within_income_contribution_percent_initial:.1f} & "
            f"{same_source} \\\\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            r"}",
            r"\begin{minipage}{0.98\textwidth}",
            r"\footnotesize",
            (
                r"\textit{Note:} Total change, education, and within-group "
                r"components are percentages of initial synthetic monthly income. "
                r"The underlying income measure is 2017 PPP US dollars per "
                r"employed person per month. "
                r"The two components add to total change before rounding. "
                r"``Same source'' indicates that the Tableau series and "
                r"survey identifiers are unchanged across endpoints."
            ),
            r"\end{minipage}",
            r"\end{table}",
            "",
        ]
    )
    return "\n".join(lines)


def validate(
    countries: pd.DataFrame,
    groups: pd.DataFrame,
    selected: pd.DataFrame,
) -> dict[str, object]:
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
    joined = countries.set_index("country").join(
        group_sums,
        rsuffix="_groups",
        validate="one_to_one",
    )
    checks = {
        "countries": int(len(countries)),
        "selected_endpoints": int(len(selected)),
        "all_endpoints_q4": bool(
            selected["period"].str.endswith("-Q4").all()
        ),
        "two_endpoints_per_country": bool(
            selected.groupby("country")["endpoint"]
            .nunique()
            .eq(2)
            .all()
        ),
        "maximum_share_sum_error": float(
            max(
                (joined["share_0"] - 1).abs().max(),
                (joined["share_1"] - 1).abs().max(),
            )
        ),
        "maximum_country_identity_error": float(
            countries["residual_usd_2017_ppp"].abs().max()
        ),
        "maximum_group_education_sum_error": float(
            (
                joined["education_component"]
                - joined["education_component_usd_2017_ppp"]
            )
            .abs()
            .max()
        ),
        "maximum_group_within_sum_error": float(
            (
                joined["within_component"]
                - joined["within_income_component_usd_2017_ppp"]
            )
            .abs()
            .max()
        ),
        "maximum_absolute_income_reconstruction_error": float(
            countries[
                [
                    "income_reconstruction_error_0",
                    "income_reconstruction_error_1",
                ]
            ]
            .abs()
            .to_numpy()
            .max()
        ),
        "maximum_absolute_worker_reconstruction_error": float(
            countries[
                [
                    "worker_reconstruction_error_0",
                    "worker_reconstruction_error_1",
                ]
            ]
            .abs()
            .to_numpy()
            .max()
        ),
        "countries_with_source_change": int(
            (~countries["same_source"]).sum()
        ),
    }
    tolerance = 1e-9
    passed = bool(
        checks["all_endpoints_q4"]
        and checks["two_endpoints_per_country"]
        and checks["maximum_share_sum_error"] <= tolerance
        and checks["maximum_country_identity_error"] <= tolerance
        and checks["maximum_group_education_sum_error"] <= tolerance
        and checks["maximum_group_within_sum_error"] <= tolerance
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "tolerance": tolerance,
        "checks": checks,
    }


def main() -> None:
    cells, candidates, _ = build_source_candidates()
    selected, audit = select_endpoints(candidates)
    countries, groups, descriptives = build_outputs(cells, selected)
    validation = validate(countries, groups, selected)
    if validation["status"] != "PASS":
        raise ValueError(json.dumps(validation, indent=2))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    candidates.to_csv(
        OUTPUT_DIR / "source_year_candidates.csv", index=False
    )
    audit.to_csv(OUTPUT_DIR / "source_selection_audit.csv", index=False)
    selected.to_csv(OUTPUT_DIR / "selected_endpoints.csv", index=False)
    countries.to_csv(
        OUTPUT_DIR / "country_decompositions.csv", index=False
    )
    groups.to_csv(
        OUTPUT_DIR / "country_education_components.csv", index=False
    )
    descriptives.to_csv(
        OUTPUT_DIR / "country_endpoint_descriptives.csv", index=False
    )
    with (OUTPUT_DIR / "validation_summary.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(validation, handle, ensure_ascii=False, indent=2)

    (TABLE_DIR / "latam_country_income_descriptives.tex").write_text(
        format_income_table(countries), encoding="utf-8"
    )
    (TABLE_DIR / "latam_country_education_shares.tex").write_text(
        format_composition_table(countries), encoding="utf-8"
    )
    (TABLE_DIR / "latam_country_education_incomes.tex").write_text(
        format_group_income_table(countries), encoding="utf-8"
    )
    (TABLE_DIR / "latam_country_decomposition.tex").write_text(
        format_decomposition_table(countries), encoding="utf-8"
    )

    print(json.dumps(validation, ensure_ascii=False, indent=2))
    print()
    print(
        countries[
            [
                "country",
                "start_year",
                "end_year",
                "same_source",
                "percent_change",
                "education_contribution_percent_initial",
                "within_income_contribution_percent_initial",
                "income_reconstruction_error_0",
                "income_reconstruction_error_1",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
