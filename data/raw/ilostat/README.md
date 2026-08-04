# ILOSTAT raw tables

Downloaded on 2026-08-03 with the official `Rilostat` package.

## Files

- `EAR_EMTA_SEX_EDU_NB_A.csv.gz`: average monthly earnings of employees by
  sex and education, local currency, annual frequency.
- `EMP_TEMP_SEX_STE_EDU_NB_A.csv.gz`: employment by sex, status in employment,
  and education, thousands, annual frequency.

The global paper matches both tables by country, year, statistical source, and
aggregate educational attainment. Employment weights are restricted to total
sex and `STE_AGGREGATE_EES` (employees).

The annual-frequency label does not by itself guarantee that every observation
is a full-year average. Source notes and reference periods must be checked
before finalizing country comparison windows.

Source: https://ilostat.ilo.org/data/
