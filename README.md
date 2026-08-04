# GlobalEducation

This repository contains two related papers that use the same exact
decomposition but study different populations.

## Manuscripts

- `main.tex` compiles the global paper, whose source is `global.tex`.
- `latam.tex` compiles the Latin American paper.
- `tex/shared_decomposition.tex` contains the accounting identity used by both
  papers.

The global paper studies monthly wages of employees using annual ILOSTAT data.
The Latin American paper studies monthly labor income of all employed workers
using the World Bank's LAC Equity Lab. Their observations should not be pooled
because the populations and remuneration concepts differ.

## Data and code

- `code/00_audit_lablac.py` audits the LABLAC aggregates.
- `code/01_download_ilostat.R` downloads the two annual ILOSTAT tables.
- `code/02_audit_ilostat_global.py` matches the ILOSTAT tables and creates
  coverage and reconstruction diagnostics.
- `data/raw/world_bank_lablac/` contains the original LABLAC package and the
  extracted source files.
- `data/raw/ilostat/` contains the compressed ILOSTAT downloads.
- `data/processed/ilostat/` contains the global coverage audit outputs.

The ILOSTAT downloader requires the R package `Rilostat`. The audit scripts
require Python and `pandas`.

## Overleaf

The default Overleaf main document is `main.tex`, which compiles the global
paper. To compile the Latin American paper, select `latam.tex` as the main
document in Overleaf.

## Research design

`notes/two_paper_design.md` records the distinction between the two papers,
their preliminary coverage, and the decisions that must remain separate.
