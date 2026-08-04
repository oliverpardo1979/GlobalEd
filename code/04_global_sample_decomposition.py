"""Build exact wage-growth decompositions for common international panels.

The script produces two conceptually distinct aggregates:

1. fixed country weights, which average within-country changes and preserve
   the original two-part education/remuneration decomposition; and
2. changing country weights, which adds an exact between-country composition
   component.

Nominal ILOSTAT earnings are deflated with the World Bank CPI and converted to
constant 2021 international dollars with the 2021 private-consumption PPP.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ILO_RAW_DIR = ROOT / "data" / "raw" / "ilostat"
WDI_RAW_DIR = ROOT / "data" / "raw" / "world_bank_wdi"
OUTPUT_DIR = ROOT / "data" / "processed" / "global_decomposition"
TABLE_DIR = ROOT / "tables"

EARNINGS_FILE = ILO_RAW_DIR / "EAR_EMTA_SEX_EDU_NB_A.csv.gz"
EMPLOYMENT_FILE = ILO_RAW_DIR / "EMP_TEMP_SEX_STE_EDU_NB_A.csv.gz"

CPI_FILE = WDI_RAW_DIR / "FP_CPI_TOTL.csv"
PRIVATE_PPP_FILE = WDI_RAW_DIR / "PA_NUS_PRVT_PP.csv"

PPP_YEAR = 2021
MAX_RECONSTRUCTION_ERROR = 0.05
MAX_UNKNOWN_EDUCATION_SHARE = 0.05
MAX_ANNUAL_EDUCATION_SHARE_CHANGE = 0.10

SHARE_JUMP_SCREENS = {
    "baseline_10pp": MAX_ANNUAL_EDUCATION_SHARE_CHANGE,
    "strict_5pp": 0.05,
    "no_share_jump_screen": None,
}

WINDOWS = [
    (2010, 2019),
    (2015, 2019),
    (2019, 2023),
]

EDUCATION = [
    "EDU_AGGREGATE_LTB",
    "EDU_AGGREGATE_BAS",
    "EDU_AGGREGATE_INT",
    "EDU_AGGREGATE_ADV",
]

EDUCATION_LABELS = {
    "EDU_AGGREGATE_LTB": "Less than basic",
    "EDU_AGGREGATE_BAS": "Basic",
    "EDU_AGGREGATE_INT": "Intermediate",
    "EDU_AGGREGATE_ADV": "Advanced",
}


def extract_note_value(series: pd.Series, pattern: str) -> pd.Series:
    extracted = series.fillna("").str.extract(pattern, flags=re.IGNORECASE)[0]
    return extracted.str.strip().replace("", np.nan)


def load_ilostat_cells() -> tuple[pd.DataFrame, pd.DataFrame]:
    earnings_raw = pd.read_csv(EARNINGS_FILE)
    employment_raw = pd.read_csv(EMPLOYMENT_FILE)

    earnings = earnings_raw[
        (earnings_raw["sex"] == "SEX_T")
        & earnings_raw["classif1"].isin(EDUCATION)
    ][
        [
            "ref_area",
            "ref_area.label",
            "source",
            "source.label",
            "time",
            "classif1",
            "obs_value",
            "obs_status",
            "obs_status.label",
            "note_indicator.label",
            "note_source.label",
        ]
    ].rename(
        columns={
            "ref_area.label": "country",
            "source.label": "source_label",
            "classif1": "education",
            "obs_value": "nominal_wage",
            "obs_status": "wage_status",
            "obs_status.label": "wage_status_label",
            "note_indicator.label": "wage_indicator_note",
            "note_source.label": "wage_source_note",
        }
    )

    employment = employment_raw[
        (employment_raw["sex"] == "SEX_T")
        & (employment_raw["classif1"] == "STE_AGGREGATE_EES")
        & employment_raw["classif2"].isin(EDUCATION)
    ][
        [
            "ref_area",
            "source",
            "time",
            "classif2",
            "obs_value",
            "obs_status",
            "obs_status.label",
            "note_indicator.label",
            "note_source.label",
        ]
    ].rename(
        columns={
            "classif2": "education",
            "obs_value": "employees_thousands",
            "obs_status": "employment_status",
            "obs_status.label": "employment_status_label",
            "note_indicator.label": "employment_indicator_note",
            "note_source.label": "employment_source_note",
        }
    )

    keys = ["ref_area", "source", "time", "education"]
    cells = earnings.merge(
        employment,
        on=keys,
        how="inner",
        validate="one_to_one",
    )

    cells["currency_code"] = extract_note_value(
        cells["wage_indicator_note"], r"Currency:\s*([A-Z]{3})"
    )
    wage_reference = extract_note_value(
        cells["wage_source_note"], r"Data reference period:\s*([^|]+)"
    )
    employment_reference = extract_note_value(
        cells["employment_source_note"],
        r"Data reference period:\s*([^|]+)",
    )
    cells["reference_period_mismatch"] = (
        wage_reference.notna()
        & employment_reference.notna()
        & wage_reference.ne(employment_reference)
    )
    cells["reference_period"] = (
        wage_reference.fillna(employment_reference).fillna("Not stated")
    )

    break_text = (
        cells[
            [
                "wage_status",
                "wage_status_label",
                "employment_status",
                "employment_status_label",
                "wage_indicator_note",
                "employment_indicator_note",
                "wage_source_note",
                "employment_source_note",
            ]
        ]
        .fillna("")
        .astype(str)
        .agg(" | ".join, axis=1)
    )
    cells["break_flag"] = (
        cells["wage_status"].fillna("").eq("B")
        | cells["employment_status"].fillna("").eq("B")
        | break_text.str.contains("break in series", case=False, regex=False)
    )

    year_quality = build_year_quality(cells, earnings_raw, employment_raw)
    return cells, year_quality


def build_year_quality(
    cells: pd.DataFrame,
    earnings_raw: pd.DataFrame,
    employment_raw: pd.DataFrame,
) -> pd.DataFrame:
    total_earnings = earnings_raw[
        (earnings_raw["sex"] == "SEX_T")
        & (earnings_raw["classif1"] == "EDU_AGGREGATE_TOTAL")
    ][["ref_area", "source", "time", "obs_value"]].rename(
        columns={"obs_value": "published_total_wage"}
    )
    total_employment = employment_raw[
        (employment_raw["sex"] == "SEX_T")
        & (employment_raw["classif1"] == "STE_AGGREGATE_EES")
        & (employment_raw["classif2"] == "EDU_AGGREGATE_TOTAL")
    ][["ref_area", "source", "time", "obs_value"]].rename(
        columns={"obs_value": "published_total_employees"}
    )
    unknown_employment = employment_raw[
        (employment_raw["sex"] == "SEX_T")
        & (employment_raw["classif1"] == "STE_AGGREGATE_EES")
        & (employment_raw["classif2"] == "EDU_AGGREGATE_X")
    ][["ref_area", "source", "time", "obs_value"]].rename(
        columns={"obs_value": "unknown_education_employees"}
    )

    cells = cells.copy()
    cells["payroll"] = cells["nominal_wage"] * cells["employees_thousands"]
    cells["positive_cell"] = (
        cells["nominal_wage"].gt(0) & cells["employees_thousands"].gt(0)
    )

    quality = (
        cells.groupby(
            [
                "ref_area",
                "country",
                "source",
                "source_label",
                "time",
            ],
            as_index=False,
        )
        .agg(
            education_groups=("education", "nunique"),
            stated_education_employees=("employees_thousands", "sum"),
            payroll=("payroll", "sum"),
            all_cells_positive=("positive_cell", "all"),
            currency_codes=("currency_code", "nunique"),
            currency_code=("currency_code", "first"),
            reference_periods=("reference_period", "nunique"),
            reference_period=("reference_period", "first"),
            reference_period_mismatch=("reference_period_mismatch", "any"),
            break_flag=("break_flag", "any"),
        )
    )
    quality["reconstructed_wage"] = (
        quality["payroll"] / quality["stated_education_employees"]
    )
    quality = (
        quality.merge(
            total_earnings,
            on=["ref_area", "source", "time"],
            how="left",
            validate="one_to_one",
        )
        .merge(
            total_employment,
            on=["ref_area", "source", "time"],
            how="left",
            validate="one_to_one",
        )
        .merge(
            unknown_employment,
            on=["ref_area", "source", "time"],
            how="left",
            validate="one_to_one",
        )
    )
    quality["unknown_education_employees"] = quality[
        "unknown_education_employees"
    ].fillna(0)
    quality["relative_reconstruction_error"] = (
        quality["reconstructed_wage"] - quality["published_total_wage"]
    ) / quality["published_total_wage"]
    quality["unknown_education_share"] = (
        quality["unknown_education_employees"]
        / quality["published_total_employees"]
    )

    quality["clean_year"] = (
        quality["education_groups"].eq(len(EDUCATION))
        & quality["all_cells_positive"]
        & quality["currency_codes"].eq(1)
        & quality["reference_periods"].eq(1)
        & ~quality["reference_period_mismatch"]
        & quality["published_total_wage"].gt(0)
        & quality["published_total_employees"].gt(0)
        & quality["relative_reconstruction_error"]
        .abs()
        .le(MAX_RECONSTRUCTION_ERROR)
        & quality["unknown_education_share"].le(
            MAX_UNKNOWN_EDUCATION_SHARE
        )
    )
    return quality


def load_wdi() -> tuple[pd.DataFrame, pd.DataFrame]:
    cpi = pd.read_csv(CPI_FILE).rename(columns={"value": "cpi"})
    ppp = pd.read_csv(PRIVATE_PPP_FILE).rename(
        columns={"value": "private_consumption_ppp"}
    )
    return cpi, ppp


def build_window_source_audit(
    cells: pd.DataFrame,
    quality: pd.DataFrame,
    cpi: pd.DataFrame,
    ppp: pd.DataFrame,
    maximum_annual_share_change: float | None,
) -> pd.DataFrame:
    cpi_lookup = cpi.set_index(["country_code", "year"])["cpi"]
    ppp_lookup = ppp.set_index(["country_code", "year"])[
        "private_consumption_ppp"
    ]
    rows: list[dict[str, object]] = []

    for start_year, end_year in WINDOWS:
        expected_years = set(range(start_year, end_year + 1))
        for (country_code, source), source_data in quality.groupby(
            ["ref_area", "source"], sort=False
        ):
            window = source_data[
                source_data["time"].between(start_year, end_year)
            ].sort_values("time")
            years = set(window["time"].astype(int))
            full_window = years == expected_years
            all_years_clean = bool(
                full_window and window["clean_year"].all()
            )
            stable_currency = bool(
                full_window
                and window["currency_code"].notna().all()
                and window["currency_code"].nunique() == 1
            )
            stable_reference_period = bool(
                full_window and window["reference_period"].nunique() == 1
            )
            no_internal_break = bool(
                full_window
                and not window.loc[
                    window["time"].gt(start_year), "break_flag"
                ].any()
            )
            composition = cells[
                (cells["ref_area"] == country_code)
                & (cells["source"] == source)
                & cells["time"].between(start_year, end_year)
            ][["time", "education", "employees_thousands"]].copy()
            if full_window and not composition.empty:
                composition["education_share"] = (
                    composition["employees_thousands"]
                    / composition.groupby("time")[
                        "employees_thousands"
                    ].transform("sum")
                )
                share_panel = composition.pivot(
                    index="time",
                    columns="education",
                    values="education_share",
                ).sort_index()
                max_annual_share_change = float(
                    share_panel.diff().abs().max().max()
                )
            else:
                max_annual_share_change = np.nan
            stable_education_distribution = bool(
                full_window
                and (
                    maximum_annual_share_change is None
                    or max_annual_share_change
                    <= maximum_annual_share_change
                )
            )

            required_wdi_keys = [
                (country_code, start_year),
                (country_code, end_year),
                (country_code, PPP_YEAR),
            ]
            complete_cpi = all(key in cpi_lookup.index for key in required_wdi_keys)
            complete_ppp = (country_code, PPP_YEAR) in ppp_lookup.index
            wdi_complete = bool(complete_cpi and complete_ppp)

            rows.append(
                {
                    "window": f"{start_year}-{end_year}",
                    "start_year": start_year,
                    "end_year": end_year,
                    "country_code": country_code,
                    "country": source_data["country"].iloc[0],
                    "source": source,
                    "source_label": source_data["source_label"].iloc[0],
                    "full_window": full_window,
                    "all_years_clean": all_years_clean,
                    "stable_currency": stable_currency,
                    "stable_reference_period": stable_reference_period,
                    "no_internal_break": no_internal_break,
                    "stable_education_distribution": (
                        stable_education_distribution
                    ),
                    "max_annual_education_share_change": (
                        max_annual_share_change
                    ),
                    "wdi_complete": wdi_complete,
                    "eligible": (
                        full_window
                        and all_years_clean
                        and stable_currency
                        and stable_reference_period
                        and no_internal_break
                        and stable_education_distribution
                        and wdi_complete
                    ),
                    "currency_code": (
                        window["currency_code"].iloc[0]
                        if full_window and len(window)
                        else np.nan
                    ),
                    "reference_period": (
                        window["reference_period"].iloc[0]
                        if full_window and len(window)
                        else np.nan
                    ),
                    "midpoint_employees_thousands": (
                        float(
                            window.loc[
                                window["time"].isin(
                                    [start_year, end_year]
                                ),
                                "stated_education_employees",
                            ].mean()
                        )
                        if full_window
                        else np.nan
                    ),
                    "max_abs_reconstruction_error": (
                        float(
                            window["relative_reconstruction_error"].abs().max()
                        )
                        if full_window
                        else np.nan
                    ),
                    "max_unknown_education_share": (
                        float(window["unknown_education_share"].max())
                        if full_window
                        else np.nan
                    ),
                }
            )

    audit = pd.DataFrame(rows)
    eligible = audit[audit["eligible"]].copy()
    eligible = eligible.sort_values(
        [
            "window",
            "country_code",
            "midpoint_employees_thousands",
            "max_abs_reconstruction_error",
            "source",
        ],
        ascending=[True, True, False, True, True],
    )
    selected_keys = eligible.drop_duplicates(
        ["window", "country_code"]
    )[["window", "country_code", "source"]].assign(selected=True)
    audit = audit.merge(
        selected_keys,
        on=["window", "country_code", "source"],
        how="left",
        validate="one_to_one",
    )
    audit["selected"] = audit["selected"].fillna(False).astype(bool)
    return audit


def decompose_countries(
    cells: pd.DataFrame,
    source_audit: pd.DataFrame,
    cpi: pd.DataFrame,
    ppp: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    cpi_lookup = cpi.set_index(["country_code", "year"])["cpi"]
    ppp_lookup = ppp.set_index(["country_code", "year"])[
        "private_consumption_ppp"
    ]

    country_rows: list[dict[str, object]] = []
    group_rows: list[dict[str, object]] = []

    for selected in source_audit[source_audit["selected"]].itertuples():
        start_year = int(selected.start_year)
        end_year = int(selected.end_year)
        country_code = selected.country_code
        source = selected.source
        country_cells = cells[
            (cells["ref_area"] == country_code)
            & (cells["source"] == source)
            & cells["time"].isin([start_year, end_year])
        ].copy()
        if len(country_cells) != 2 * len(EDUCATION):
            raise AssertionError(
                f"Unexpected endpoint cell count for {country_code}, "
                f"{source}, {start_year}-{end_year}"
            )

        cpi_anchor = float(cpi_lookup.loc[(country_code, PPP_YEAR)])
        ppp_anchor = float(ppp_lookup.loc[(country_code, PPP_YEAR)])
        country_cells["real_wage_ppp_2021"] = country_cells.apply(
            lambda row: (
                row["nominal_wage"]
                * cpi_anchor
                / float(cpi_lookup.loc[(country_code, int(row["time"]))])
                / ppp_anchor
            ),
            axis=1,
        )

        start = country_cells[country_cells["time"] == start_year].set_index(
            "education"
        )
        end = country_cells[country_cells["time"] == end_year].set_index(
            "education"
        )
        employees_0 = float(start["employees_thousands"].sum())
        employees_1 = float(end["employees_thousands"].sum())
        shares_0 = start["employees_thousands"] / employees_0
        shares_1 = end["employees_thousands"] / employees_1
        wages_0 = start["real_wage_ppp_2021"]
        wages_1 = end["real_wage_ppp_2021"]

        mean_wage_0 = float((shares_0 * wages_0).sum())
        mean_wage_1 = float((shares_1 * wages_1).sum())
        education_component = float(
            (((wages_0 + wages_1) / 2) * (shares_1 - shares_0)).sum()
        )
        within_wage_component = float(
            (((shares_0 + shares_1) / 2) * (wages_1 - wages_0)).sum()
        )
        change = mean_wage_1 - mean_wage_0
        residual = change - education_component - within_wage_component

        country_rows.append(
            {
                "window": selected.window,
                "start_year": start_year,
                "end_year": end_year,
                "country_code": country_code,
                "country": selected.country,
                "source": source,
                "source_label": selected.source_label,
                "currency_code": selected.currency_code,
                "reference_period": selected.reference_period,
                "employees_0_thousands": employees_0,
                "employees_1_thousands": employees_1,
                "mean_wage_0_ppp_2021": mean_wage_0,
                "mean_wage_1_ppp_2021": mean_wage_1,
                "change_ppp_2021": change,
                "education_component_ppp_2021": education_component,
                "within_wage_component_ppp_2021": within_wage_component,
                "residual_ppp_2021": residual,
                "percent_change": 100 * change / mean_wage_0,
                "annualized_percent_change": 100
                * ((mean_wage_1 / mean_wage_0) ** (1 / (end_year - start_year)) - 1),
            }
        )

        for education in EDUCATION:
            group_rows.append(
                {
                    "window": selected.window,
                    "start_year": start_year,
                    "end_year": end_year,
                    "country_code": country_code,
                    "country": selected.country,
                    "source": source,
                    "education": education,
                    "education_label": EDUCATION_LABELS[education],
                    "share_0": float(shares_0.loc[education]),
                    "share_1": float(shares_1.loc[education]),
                    "wage_0_ppp_2021": float(wages_0.loc[education]),
                    "wage_1_ppp_2021": float(wages_1.loc[education]),
                    "education_component_ppp_2021": float(
                        ((wages_0.loc[education] + wages_1.loc[education]) / 2)
                        * (shares_1.loc[education] - shares_0.loc[education])
                    ),
                    "within_wage_component_ppp_2021": float(
                        ((shares_0.loc[education] + shares_1.loc[education]) / 2)
                        * (wages_1.loc[education] - wages_0.loc[education])
                    ),
                }
            )

    return pd.DataFrame(country_rows), pd.DataFrame(group_rows)


def aggregate_decompositions(
    countries: pd.DataFrame,
    groups: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    aggregate_rows: list[dict[str, object]] = []
    aggregate_group_rows: list[dict[str, object]] = []

    for window, country_data in countries.groupby("window", sort=False):
        country_data = country_data.copy().reset_index(drop=True)
        n_countries = len(country_data)
        q0 = (
            country_data["employees_0_thousands"]
            / country_data["employees_0_thousands"].sum()
        )
        q1 = (
            country_data["employees_1_thousands"]
            / country_data["employees_1_thousands"].sum()
        )
        qbar = (q0 + q1) / 2
        qfixed = (
            country_data["employees_0_thousands"]
            + country_data["employees_1_thousands"]
        )
        qfixed = qfixed / qfixed.sum()
        qequal = pd.Series(1 / n_countries, index=country_data.index)

        weights = {
            "fixed_employment_weights": qfixed,
            "equal_country_weights": qequal,
            "changing_employment_weights": qbar,
        }

        for method, weight in weights.items():
            if method == "changing_employment_weights":
                mean_0 = float(
                    (q0 * country_data["mean_wage_0_ppp_2021"]).sum()
                )
                mean_1 = float(
                    (q1 * country_data["mean_wage_1_ppp_2021"]).sum()
                )
                country_composition = float(
                    (
                        ((country_data["mean_wage_0_ppp_2021"]
                          + country_data["mean_wage_1_ppp_2021"]) / 2)
                        * (q1 - q0)
                    ).sum()
                )
            else:
                mean_0 = float(
                    (weight * country_data["mean_wage_0_ppp_2021"]).sum()
                )
                mean_1 = float(
                    (weight * country_data["mean_wage_1_ppp_2021"]).sum()
                )
                country_composition = 0.0

            education = float(
                (
                    weight
                    * country_data["education_component_ppp_2021"]
                ).sum()
            )
            within_wage = float(
                (
                    weight
                    * country_data["within_wage_component_ppp_2021"]
                ).sum()
            )
            change = mean_1 - mean_0
            residual = change - education - within_wage - country_composition
            years = int(country_data["end_year"].iloc[0]) - int(
                country_data["start_year"].iloc[0]
            )

            aggregate_rows.append(
                {
                    "window": window,
                    "start_year": int(country_data["start_year"].iloc[0]),
                    "end_year": int(country_data["end_year"].iloc[0]),
                    "aggregation": method,
                    "n_countries": n_countries,
                    "employees_0_thousands": float(
                        country_data["employees_0_thousands"].sum()
                    ),
                    "employees_1_thousands": float(
                        country_data["employees_1_thousands"].sum()
                    ),
                    "mean_wage_0_ppp_2021": mean_0,
                    "mean_wage_1_ppp_2021": mean_1,
                    "change_ppp_2021": change,
                    "education_component_ppp_2021": education,
                    "within_wage_component_ppp_2021": within_wage,
                    "country_composition_component_ppp_2021": country_composition,
                    "residual_ppp_2021": residual,
                    "percent_change": 100 * change / mean_0,
                    "annualized_percent_change": 100
                    * ((mean_1 / mean_0) ** (1 / years) - 1),
                    "education_contribution_percent_initial": (
                        100 * education / mean_0
                    ),
                    "within_wage_contribution_percent_initial": (
                        100 * within_wage / mean_0
                    ),
                    "country_composition_contribution_percent_initial": (
                        100 * country_composition / mean_0
                    ),
                }
            )

            method_groups = groups[groups["window"] == window].merge(
                country_data[["country_code"]].assign(weight=weight.values),
                on="country_code",
                how="inner",
                validate="many_to_one",
            )
            grouped = (
                method_groups.groupby(
                    ["education", "education_label"], as_index=False
                )
                .apply(
                    lambda frame: pd.Series(
                        {
                            "education_component_ppp_2021": (
                                frame["weight"]
                                * frame["education_component_ppp_2021"]
                            ).sum(),
                            "within_wage_component_ppp_2021": (
                                frame["weight"]
                                * frame["within_wage_component_ppp_2021"]
                            ).sum(),
                        }
                    ),
                    include_groups=False,
                )
                .reset_index(drop=True)
            )
            grouped["window"] = window
            grouped["aggregation"] = method
            aggregate_group_rows.extend(grouped.to_dict("records"))

    return pd.DataFrame(aggregate_rows), pd.DataFrame(aggregate_group_rows)


def build_coverage_summary(source_audit: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for window, audit in source_audit.groupby("window", sort=False):
        rows.append(
            {
                "window": window,
                "country_source_series": int(len(audit)),
                "sources_with_full_window": int(audit["full_window"].sum()),
                "sources_with_clean_years": int(
                    (audit["full_window"] & audit["all_years_clean"]).sum()
                ),
                "sources_with_stable_currency": int(
                    (
                        audit["full_window"]
                        & audit["all_years_clean"]
                        & audit["stable_currency"]
                    ).sum()
                ),
                "sources_with_stable_reference_period": int(
                    (
                        audit["full_window"]
                        & audit["all_years_clean"]
                        & audit["stable_currency"]
                        & audit["stable_reference_period"]
                    ).sum()
                ),
                "sources_without_internal_break": int(
                    (
                        audit["full_window"]
                        & audit["all_years_clean"]
                        & audit["stable_currency"]
                        & audit["stable_reference_period"]
                        & audit["no_internal_break"]
                    ).sum()
                ),
                "sources_with_stable_education_distribution": int(
                    (
                        audit["full_window"]
                        & audit["all_years_clean"]
                        & audit["stable_currency"]
                        & audit["stable_reference_period"]
                        & audit["no_internal_break"]
                        & audit["stable_education_distribution"]
                    ).sum()
                ),
                "eligible_sources_with_wdi": int(audit["eligible"].sum()),
                "selected_countries": int(audit["selected"].sum()),
            }
        )
    return pd.DataFrame(rows)


def format_table(aggregates: pd.DataFrame) -> str:
    labels = {
        "fixed_employment_weights": "Fixed employment weights",
        "equal_country_weights": "Equal country weights",
        "changing_employment_weights": "Changing employment weights",
    }
    rows = []
    for row in aggregates.itertuples():
        rows.append(
            " & ".join(
                [
                    row.window.replace("-", "--"),
                    labels[row.aggregation],
                    f"{row.n_countries}",
                    f"{row.percent_change:.1f}",
                    f"{row.education_contribution_percent_initial:.1f}",
                    f"{row.within_wage_contribution_percent_initial:.1f}",
                    (
                        f"{row.country_composition_contribution_percent_initial:.1f}"
                        if row.aggregation == "changing_employment_weights"
                        else "---"
                    ),
                ]
            )
            + r" \\"
        )

    body = "\n".join(rows)
    return rf"""\begin{{table}}[htbp]
\centering
\caption{{Aggregate decomposition of real monthly wage growth}}
\label{{tab:global_sample_decomposition}}
\resizebox{{\textwidth}}{{!}}{{%
\begin{{tabular}}{{llrrrrr}}
\toprule
Window & Country weights & Countries & Total & Education & Within wage & Country mix \\
 & & & \multicolumn{{4}}{{c}}{{Percent of initial mean wage}} \\
\midrule
{body}
\bottomrule
\end{{tabular}}%
}}
\begin{{minipage}}{{0.96\textwidth}}
\textit{{Notes:}} Nominal monthly earnings are converted to constant 2021
international dollars with national consumer price indexes and the World
Bank private-consumption PPP for 2021. Fixed employment weights use each
country's average number of employees at the two endpoints. Changing weights
allow each country's share of sample employment to vary and therefore add the
country-mix component. Components are exactly additive before rounding.
\end{{minipage}}
\end{{table}}
"""


def main() -> None:
    cells, quality = load_ilostat_cells()
    cpi, ppp = load_wdi()
    specifications = {}
    for screen_label, threshold in SHARE_JUMP_SCREENS.items():
        source_audit = build_window_source_audit(
            cells,
            quality,
            cpi,
            ppp,
            maximum_annual_share_change=threshold,
        )
        countries, groups = decompose_countries(
            cells, source_audit, cpi, ppp
        )
        aggregates, aggregate_groups = aggregate_decompositions(
            countries, groups
        )
        coverage = build_coverage_summary(source_audit)
        for frame in [
            source_audit,
            countries,
            groups,
            aggregates,
            aggregate_groups,
            coverage,
        ]:
            frame.insert(0, "share_jump_screen", screen_label)
        specifications[screen_label] = {
            "source_audit": source_audit,
            "countries": countries,
            "groups": groups,
            "aggregates": aggregates,
            "aggregate_groups": aggregate_groups,
            "coverage": coverage,
        }

    baseline = specifications["baseline_10pp"]
    source_audit = baseline["source_audit"]
    countries = baseline["countries"]
    groups = baseline["groups"]
    aggregates = baseline["aggregates"]
    aggregate_groups = baseline["aggregate_groups"]
    coverage = baseline["coverage"]
    sensitivity_aggregates = pd.concat(
        [result["aggregates"] for result in specifications.values()],
        ignore_index=True,
    )
    sensitivity_coverage = pd.concat(
        [result["coverage"] for result in specifications.values()],
        ignore_index=True,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    source_audit.to_csv(OUTPUT_DIR / "window_source_audit.csv", index=False)
    coverage.to_csv(OUTPUT_DIR / "window_coverage_summary.csv", index=False)
    countries.to_csv(OUTPUT_DIR / "country_decompositions.csv", index=False)
    groups.to_csv(
        OUTPUT_DIR / "country_education_contributions.csv", index=False
    )
    aggregates.to_csv(
        OUTPUT_DIR / "aggregate_decompositions.csv", index=False
    )
    aggregate_groups.to_csv(
        OUTPUT_DIR / "aggregate_education_contributions.csv", index=False
    )
    sensitivity_aggregates.to_csv(
        OUTPUT_DIR / "sensitivity_aggregate_decompositions.csv",
        index=False,
    )
    sensitivity_coverage.to_csv(
        OUTPUT_DIR / "sensitivity_window_coverage.csv", index=False
    )
    (TABLE_DIR / "global_sample_decomposition.tex").write_text(
        format_table(aggregates), encoding="utf-8"
    )

    maximum_country_residual = float(countries["residual_ppp_2021"].abs().max())
    maximum_aggregate_residual = float(
        aggregates["residual_ppp_2021"].abs().max()
    )
    summary = {
        "ppp_year": PPP_YEAR,
        "quality_thresholds": {
            "maximum_absolute_reconstruction_error": (
                MAX_RECONSTRUCTION_ERROR
            ),
            "maximum_unknown_education_share": (
                MAX_UNKNOWN_EDUCATION_SHARE
            ),
            "maximum_annual_education_share_change": (
                MAX_ANNUAL_EDUCATION_SHARE_CHANGE
            ),
        },
        "windows": coverage.to_dict("records"),
        "maximum_absolute_country_residual": maximum_country_residual,
        "maximum_absolute_aggregate_residual": maximum_aggregate_residual,
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
                "within_wage_contribution_percent_initial",
                "country_composition_contribution_percent_initial",
                "residual_ppp_2021",
            ]
        ].to_string(index=False)
    )
    print()
    print("Sensitivity: fixed employment weights")
    print(
        sensitivity_aggregates[
            sensitivity_aggregates["aggregation"]
            == "fixed_employment_weights"
        ][
            [
                "share_jump_screen",
                "window",
                "n_countries",
                "percent_change",
                "education_contribution_percent_initial",
                "within_wage_contribution_percent_initial",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
