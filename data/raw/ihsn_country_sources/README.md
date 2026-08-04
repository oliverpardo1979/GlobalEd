# IHSN country-source screening

This directory documents the country-by-country microdata strategy.

IHSN is used as a discovery and metadata catalogue, not as a single
microdata download service. The IHSN Central Survey Catalog links each study
to the repository that owns or distributes the files. Access conditions
therefore have to be checked survey by survey.

## Minimum inclusion criteria

A country enters the microdata exercise only when the first and last surveys:

1. belong to the same survey family or have demonstrably comparable concepts;
2. have national coverage and individual-level records;
3. identify employment status and status in employment;
4. report highest educational attainment;
5. report a usable monthly labour-income or employee-earnings measure; and
6. provide survey weights.

The preferred design uses employees and monthly employee earnings because
those concepts are easier to harmonize across countries. A broader
all-workers measure can be added only when employee and self-employment
income are comparable in both endpoint years.

## Current pilot

| Country | First year | Last year | Metadata | Microdata | Status |
|---|---:|---:|---|---|---|
| South Africa | 2019 | 2023 | Downloaded | Public, but not yet downloaded | Variable audit passed with caveat |

See `south_africa/README.md` for the source links and variable crosswalk.

## Sources

- IHSN survey catalogues: https://www.ihsn.org/survey-catalogs
- IHSN cataloguing project: https://www.ihsn.org/projects/cataloguing

