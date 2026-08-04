# World Development Indicators

These files are downloaded from the World Bank Indicators API v2 by
`code/03_download_wdi.py`.

The global decomposition uses:

- `FP.CPI.TOTL`: consumer price index (2010 = 100);
- `PA.NUS.PRVT.PP`: PPP conversion factor for private consumption, in local
  currency units per international dollar;
- `PA.NUS.PPP`: PPP conversion factor for GDP, retained for sensitivity checks.

The baseline conversion expresses nominal monthly earnings in constant 2021
international dollars. For country `c` and year `t`, the conversion is:

```text
real_wage_ppp_2021 =
    nominal_wage_t * (CPI_2021 / CPI_t) / private_consumption_PPP_2021
```

The private-consumption PPP is preferred because the outcome is employee
earnings and the intended comparison is purchasing power over consumption.
GDP PPP is retained as a robustness alternative.

Source pages:

- https://data.worldbank.org/indicator/FP.CPI.TOTL
- https://data.worldbank.org/indicator/PA.NUS.PRVT.PP
- https://data.worldbank.org/indicator/PA.NUS.PPP
- https://datahelpdesk.worldbank.org/knowledgebase/articles/889392
