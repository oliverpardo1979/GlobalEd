# South Africa: LMDSA 2019 and 2023

Metadata downloaded on 2026-08-04 from the DataFirst repository:

- `metadata_2019.json` and `metadata_2019.xml`: LMDSA 2019, catalog 846.
- `metadata_2023.json` and `metadata_2023.xml`: LMDSA 2023 v1.1, catalog 1205.

Both annual Labour Market Dynamics in South Africa files combine the four
Quarterly Labour Force Survey waves of the corresponding year. They have
national coverage, individual records, education, employment status, labour
income, and survey weights.

## Proposed employee-earnings crosswalk

| Concept | 2019 | 2023 | Audit |
|---|---|---|---|
| Highest education | `Q17EDUCATION` | `lmd2023_q17education` | Substantively the same codes |
| Employee indicator | `Q51WRK4WHOM == 1` | `lmd2023_q51wrk4whom == 1` | Same definition: working for someone else for pay |
| Monthly employee earnings | `Q54a_monthly` | `lmd2023_q54a_monthly` | Present in both; verify the 2023 label against the microdata |
| Employment status | `Status` | `lmd2023_status` | Same four codes |
| Person weight | `Weight` | `lmd2023_weight` | Present in both |

The education categories match except that code 31, "Unspecified", appears
only in 2019, and the punctuation of code 24 differs. Code 98 is "No
schooling" in both years. The analysis should treat unspecified and unknown
values as missing and map the remaining codes into low, middle, and high
attainment.

## Access status

The study is labelled public under CC BY, but DataFirst requires a free user
account before exposing the microdata download. Statistics South Africa also
publishes direct ZIP links, but automated requests from the current
environment receive an Incapsula anti-bot page instead of the ZIP. No invalid
response has been retained.

DataFirst:

- 2019: https://www.datafirst.uct.ac.za/dataportal/index.php/catalog/846
- 2023: https://www.datafirst.uct.ac.za/dataportal/index.php/catalog/1205

Statistics South Africa:

- 2019 page: https://isibaloweb.statssa.gov.za/pages/surveys/pss/lmd/2019/lmd2019.php
- 2019 ZIP: https://isibaloweb.statssa.gov.za/data/PSS/HSS/LMD/LMD2019.zip
- 2023 page: https://isibaloweb.statssa.gov.za/pages/surveys/pss/lmd/2023/lmd2023.php
- 2023 ZIP: https://isibaloweb.statssa.gov.za/data/PSS/HSS/LMD/LMD2023.zip

## Validation caveat

The 2023 DDI appears to shift several labels beginning with the earnings
block: for example, `lmd2023_q54a_monthly` is labelled "Earnings interval"
even though the corresponding 2019 variable and the variable name indicate a
monthly employee-earnings amount. The raw file and its embedded value labels
must therefore be checked before calculations begin. Until that check is
complete, comparability of the earnings measure is provisional.

