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

`partial_adjustment` (test design, leg sequence), `conversion_factors` (PWT 7.1 values,
region-mix marker), `sector_conversion` (rho ranges, targets, genset efficiencies,
illustration marker and year), `carbon_intensity` (compared countries, windows, coal factor,
biomass ratio), plus `parameters` and `ssp_baseline.demand`.

## Units and Conventions

Report text describes the configured comparison (Nigeria, South Africa, Africa); the codes
that select the data are configuration (`region.iso3`, `carbon_intensity.exclude_iso3`,
`carbon_intensity.owid_aggregate`).
