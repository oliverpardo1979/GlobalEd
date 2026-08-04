# Aggregate decomposition for the covered-country sample

## Estimand

The preferred headline is an employment-weighted average of the exact
within-country decompositions, holding country weights fixed at the average
number of employees observed at the two endpoints. This answers how much of
the real wage change among the covered countries is associated with:

1. changes in education shares within countries; and
2. changes in wages within country--education cells.

A second specification allows country employment weights to change. It adds a
between-country composition term and is an exact decomposition of the change
in the covered-country mean wage.

The estimates are not labeled as a world aggregate. The common-window samples
contain 8 countries in 2010--2019, 17 in 2015--2019, and 11 in 2019--2023
after the baseline quality screen.

## Price and currency conversion

ILOSTAT nominal monthly earnings are converted into constant 2021
international dollars:

```text
real_wage_ppp_2021 =
    nominal_wage_t * (CPI_2021 / CPI_t) / private_consumption_PPP_2021
```

The CPI and private-consumption PPP come from the World Development
Indicators. Private-consumption PPP is preferred to GDP PPP because the
comparison concerns the purchasing power of employee earnings.

## Baseline quality screen

Each country-source series must:

- contain every year in the comparison window;
- contain four mutually exclusive education groups;
- use the same ILOSTAT source throughout the window;
- keep the reported currency marker and data-reference period unchanged;
- contain no internally reported break in series;
- reconstruct the published total wage within 5 percent in every year;
- have at most 5 percent of employees with education not stated;
- have positive wages and employee counts;
- have CPI observations at both endpoints and in 2021, plus a 2021 PPP;
- contain no one-year change above 10 percentage points in any education
  share.

The last rule addresses unreported classification breaks. Brazil illustrates
the risk: between 2015 and 2016, the share with less than basic education falls
from 36.5 to 7.3 percent and the advanced share rises from 5.0 to 19.8
percent, although ILOSTAT does not mark a break. Results are also produced
without this screen and with a stricter 5-point threshold.

## Preliminary aggregate results

For 2015--2019, the fixed-employment-weight mean wage increases 6.2 percent.
Educational upgrading contributes 1.7 percent of the initial mean wage, and
wage changes within education groups contribute 4.4 percent. With changing
country weights, the mean increases 5.0 percent: the two within-country
components contribute 1.7 and 4.4 percent, while the changing country mix
subtracts 1.1 percent.

The attribution is sensitive to unreported education-classification breaks,
although the total change is not. Without the education-share jump screen, the
2015--2019 fixed-weight change is 6.4 percent, split into 4.2 percent from
educational upgrading and 2.2 percent from within-group wages. Under the
stricter 5-point screen, the total is 6.0 percent, split into 1.8 and 4.2
percent.

## Reproducible outputs

- `code/03_download_wdi.py`: downloads CPI and PPP series.
- `code/04_global_sample_decomposition.py`: constructs samples and estimates
  all decompositions.
- `code/05_validate_global_decomposition.py`: independently checks keys,
  shares, component sums, sample selection, and exact additivity.
- `data/processed/global_decomposition/`: country, education-group,
  aggregate, coverage, sensitivity, and validation outputs.
- `tables/global_sample_decomposition.tex`: generated paper table.
