# GlobalEducation

This repository contains two related papers that use the same exact
decomposition but study different populations.

## Manuscripts

- `main.tex` compiles the global paper, whose source is `global.tex`.
- `latam.tex` compiles the Latin American paper.
- `tex/shared_decomposition.tex` contains the two-part accounting identity used
  by both papers.
- `tex/shared_aggregate_decomposition.tex` extends the identity across
  economies and adds the between-economy composition term.

The global paper studies monthly wages of employees using annual ILOSTAT data.
The Latin American paper studies monthly labor income of all employed workers
using the World Bank's LAC Equity Lab. Their observations should not be pooled
because the populations and remuneration concepts differ.

## Data and code

- `code/00_audit_lablac.py` audits the LABLAC aggregates.
- `code/01_download_ilostat.R` downloads the two annual ILOSTAT tables.
- `code/02_audit_ilostat_global.py` matches the ILOSTAT tables and creates
  coverage and reconstruction diagnostics.
- `code/03_download_wdi.py` downloads CPI and PPP series from the World Bank
  Indicators API.
- `code/04_global_sample_decomposition.py` builds country endpoint pairs and
  estimates the national and aggregate decompositions.
- `code/05_validate_global_decomposition.py` independently validates keys,
  population shares, component sums, sample selection, and exact additivity.
- `code/06_lablac_decomposition.py` constructs comparable LABLAC endpoint
  pairs and estimates the Latin American decompositions.
- `code/07_validate_lablac_decomposition.py` validates the LABLAC samples,
  reconstruction errors, component sums, and exact additivity.
- `code/10_lablac_q4_country_decomposition.py` estimates the country results
  from the oldest and newest complete fourth-quarter observations.
- `code/11_validate_lablac_q4_decomposition.py` independently validates the
  fourth-quarter country decompositions.
- `code/12_plot_lablac_q4_annualized_decomposition.R` generates the annualized
  country decomposition figure.
- `code/13_lablac_q4_regional_decomposition.py` estimates the common-window
  2017-Q4--2022-Q4 aggregate for all 14 covered economies.
- `code/14_validate_lablac_q4_regional_decomposition.py` independently
  validates the regional weights, identities, annualization, and pooled means.
- `code/15_plot_lablac_q4_regional_decomposition.R` generates the annualized
  regional decomposition figure.

Raw inputs are stored under `data/raw/`. Processed ILOSTAT diagnostics are
stored under `data/processed/ilostat/`. The global and LABLAC decomposition
outputs are stored under `data/processed/global_decomposition/` and
`data/processed/lablac_decomposition/`, respectively. The fourth-quarter
country and common-window regional outputs are stored under
`data/processed/lablac_q4_decomposition/` and
`data/processed/lablac_q4_regional_decomposition/`.

The ILOSTAT downloader requires the R package `Rilostat`. The Python scripts
require `pandas`, `numpy`, and `openpyxl`.

## Reproducing the global aggregate

Starting from the downloaded ILOSTAT files:

```text
python code/03_download_wdi.py
python code/04_global_sample_decomposition.py
python code/05_validate_global_decomposition.py
```

The decomposition script generates
`tables/global_sample_decomposition.tex`, which is included directly in the
global manuscript. The validation script must finish with `status: PASS`.

To reproduce the original comparable-source Latin American windows:

```text
python code/06_lablac_decomposition.py
python code/07_validate_lablac_decomposition.py
```

To reproduce the fourth-quarter country results, the common-window regional
aggregate, and both figures used in the Latin American paper:

```text
python code/10_lablac_q4_country_decomposition.py
python code/11_validate_lablac_q4_decomposition.py
Rscript code/12_plot_lablac_q4_annualized_decomposition.R
python code/13_lablac_q4_regional_decomposition.py
python code/14_validate_lablac_q4_regional_decomposition.py
Rscript code/15_plot_lablac_q4_regional_decomposition.R
```

Both Python validation scripts must finish with `status: PASS`. The regional
baseline fixes economy weights in proportion to each economy's average
employment in 2017 and 2022. The observed-weight and equal-economy estimates
are reported as sensitivity exercises.

The preferred estimate is an employment-weighted average of within-country
changes with country weights held fixed. A second exact decomposition allows
country employment shares to change and adds a between-country composition
component. These are aggregates for the countries covered by each endpoint-pair
window, not estimates for the world as a whole.

## Overleaf

The default Overleaf main document is `main.tex`, which compiles the global
paper. To compile the Latin American paper, select `latam.tex` as the main
document in Overleaf. Both annualized decomposition figures are included in
that manuscript.

## Research design

- `notes/two_paper_design.md` records the distinction between the two papers.
- `notes/global_aggregate_method.md` records the global aggregate estimand,
  quality screen, results, sensitivities, and reproducible outputs.
- `notes/latam_aggregate_method.md` records the LABLAC endpoint construction,
  aggregate estimand, results, quality checks, and limitations.
