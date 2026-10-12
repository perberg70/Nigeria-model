# Demand Analyses (`src/demand_analysis`)

## Overview

Exploratory comparators on branch `experiment/partial-adjustment`. None of them changes the
baseline or the prototype; each prints a report that is committed beside its memo.

| Module | Report | Memo |
|---|---|---|
| `partial_adjustment.py` | `partial_adjustment/output.txt` | `partial_adjustment/MEMO.md` |
| `conversion_factors.py` | `partial_adjustment/conversion_factors_output.txt` | `partial_adjustment/CONVERSION_FACTORS.md` |
| `sector_conversion.py` | `partial_adjustment/sector_conversion_output.txt` | `partial_adjustment/SECTOR_CONVERSION.md` |
| `carbon_intensity.py` | `carbon_intensity/carbon_intensity_output.txt` | `carbon_intensity/MEMO.md` |

(paths under `data/scenario_compass_africa_r10/`)

Data gaps are logged to stderr, never into the reports: WARNING marks a value that is proxied
or taken as 0 (e.g. OWID country-years missing from a regional CO2 sum, the Africa transport
biofuel years, a missing IMAGE row), INFO a blank that was checked (IEA blank cells against
their row totals). A gap that would silently corrupt a result (an unconvertible UNSD
final-energy row, an IEA blank its row total does not confirm) is a `ValueError`.

## Key Equations

Partial-adjustment variant (`partial_adjustment.pa_path`), annual, logs of per-capita final
energy `x` and income `g`:

```
x*_t = alpha + b_target * g_t
x_t  = x_{t-1} + beta_10 * (g_t - g_{t-1}) + lambda * (x*_{t-1} - x_{t-1}) + delta_t
```

with `beta_10 = beta + eta * deviation`, `lambda = -kappa`, `b_target = -theta/kappa` from
Burke & Csereklyei (2016) Table 5 (`parameters.burke_csereklyei_2016.table5.total`). The
"current construction" it is compared with is the baseline's law (`ssp_baseline.demand`).

## Double-counting control

The variant recalibrates the R10 residual through the same law as the country path, so the
income effect is removed from the regional factor exactly once; `b_mode: static-adjusted`
switches the dynamic eta interaction off rather than injecting footnote 3's slope twice (module
docstring of `partial_adjustment.py`).

## Configuration (`config.yaml`)

`partial_adjustment` (test design, leg sequence, comparison year), `conversion_factors`
(PWT 7.1 values and splice year, GDP price bases, assumed 25th-percentile cases, region-mix
marker), `sector_conversion` (UNSD code maps and flows, rho ranges, targets, genset
efficiencies, the low-emission power case, ETP and IMAGE years, illustration marker and
year), `carbon_intensity` (compared countries and their printed labels, observed, trend,
co-movement and IMAGE years, coal factor, biomass ratio), plus `parameters`,
`ssp_baseline.demand` and `inputs.iea_generation_lines`.

## Units and Conventions

Every year, code and share that selects data or enters a calculation is configuration.
Report labels that name one of them (column years such as `var/cur50`, `tr 00-09`, the 72%
power case, the compared countries) are formatted from the same keys; the carbon-intensity
labels come from `region.name`, `region.iso3`, `carbon_intensity.owid_aggregate` and
`carbon_intensity.labels`. What stays in code: the years that only choose which levels are
printed (carbon intensity `show()` columns and section A rows), row and column offsets from
the base year, the paper's 10-year windows, prose about the committed data (the 2010 break,
the "2023" snapshot labels of `sector_conversion`), and schema labels that are the same for
any country (IEA row and column names, ETP chart and series names, IMAGE variables).
