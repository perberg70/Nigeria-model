# SSP Baseline (`src/ssp_baseline`)

## Overview

Builds, per SSP marker and per year from `time_horizon.base_year` to `end_year`, the
prototype's no-policy baseline: economy-wide fossil-and-industrial CO₂, electrification, the
low-emission share of electricity and its composition, population, and the clean-cooking income
index. The method, its denominator decision and what it deliberately does not carry are in the
module docstring of `builder.py`.

## Data Inputs

- IMAGE 3.2 SSP2021, Africa R10 (`inputs.image_dir`): electricity by source, final energy,
  GDP|PPP, population.
- IIASA SSP export for Nigeria (`inputs.iiasa`): population and GDP|PPP by SSP narrative.
- IEA 2023 current-release tables (`inputs.iea.*_current`): the anchors are cross-checked
  against them on every run; a mismatch or a missing table is an error.

## Key Equations

- Energy and emissions demand: `E(t) = E_base × (P_t/P_base) × exp(b L + q L²)`,
  `L = ln(y_t / y_base)`, with `b = ssp_baseline.demand.elasticity` and
  `q = ssp_baseline.demand.elasticity_quadratic` (Burke & Csereklyei 2016, Table 5; transferred).
- R10 efficiency residual: `T(y, ref) = [FE(y)/FE(ref)] / [P(y)/P(ref) × exp(b L + q L²)]`,
  all Africa R10, so the income effect is not counted twice.
- Fossil split: back-up generators' share of fossil generation `k = k0 × e0/e`.
- Clean-cooking index: `(income per head_t / income per head_base) ** cooking_elasticity`.

## Configuration (`config.yaml`)

`ssp_baseline.anchors`, `ssp_baseline.demand`, `ssp_baseline.envelope`, plus `scenarios`,
`time_horizon`, `inputs`. Each value carries its source and gap notes in the file.

## Outputs

`ssp_baseline.output_block` (`nigeria_baseline_block.js`, four blocks) and, with
`--update-prototype`, the same blocks spliced into `ssp_baseline.prototype_html`.

### Which prototype data are generated

| Prototype data (`NGA_DATA.*` and `REGIONAL_STATE_CLIMATE` in `africa-prototype.html`) | Source |
|---|---|
| `emissions` | Generated (BLOCK 1) |
| `power.sspBaseline` | Generated (BLOCK 2) |
| `power.popSSP` | Generated (BLOCK 3) |
| `health.pollutingIdxSSP` | Generated (BLOCK 4) |
| `observed`, `scc`, `hotDays`, `cckpNationalClimate`, `regionalClimate`, `REGIONAL_STATE_CLIMATE` | Hand-pasted from the data folders |
| `power.envelope`, `power.totalEnergy2023TJ`, `power.elasticityTotal(Quadratic)`, `health.elecCookShareOfClean2020` | Hand-written; they duplicate `ssp_baseline.*` and `etp_cooking.csv` values |

[GAP: the hand-written blocks are not regenerated, so a change to `config.yaml` or to the data
folders does not reach them. Edit them by hand in the same commit, or extend the splice.]

## References

Burke, P. J. & Csereklyei, Z. (2016). Understanding the energy-GDP elasticity: a sectoral
approach. Energy Economics 58, 199–210. https://doi.org/10.1016/j.eneco.2016.07.004
