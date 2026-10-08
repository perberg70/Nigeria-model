# Partial-adjustment variant: implementation and first results

Branch `experiment/partial-adjustment`, 2026-10-08. Implements the
elasticity coherence tests and partial-adjustment variant specified in the
Master Thesis project report
(`03_models/2026-10-08_kimi-elasticity-literature/africa-energy-demand-elasticity-assessment.pplx.md`,
sections "Elasticity coherence tests" and "Partial-adjustment variant:
equations and assumptions"). Source: Burke & Csereklyei (2016),
Energy Economics 58(C):199-210, Table 5 "total" column and footnote 3.
The baseline builder is untouched; this directory is a standalone
comparator. Run: `python partial_adjustment_variant.py` (full output in
`output.txt`).

## Test 1: shock-then-flat income (+10% at 2024, then constant)

Long-run-implied endpoint of the log energy gap: -theta/kappa x ln(1.1)
= 0.0663.

| year | current construction | annual PA | decade-step Eq 5 |
|---|---:|---:|---:|
| 2033 | 0.0349 | 0.0496 | 0.0457 |
| 2053 | 0.0349 | 0.0558 | 0.0541 |
| 2073 | 0.0349 | 0.0597 | 0.0591 |
| 2100 | 0.0349 | 0.0628 | n/a |

As predicted: the current construction jumps once and stops (it has no
state variable), while both partial-adjustment paths keep converging toward
0.0663 with the ~30-year half-life implied by kappa = -0.023/yr. The
current construction permanently undershoots the paper's own long-run
response to a lasting income difference by about half. The annual
approximation tracks the decade recursion within ~0.004 log points after
2033, so the annual grid is acceptable for scenario use.

## Scenario runs (2100 final energy, variant / current)

R recalibrated through the same variant law (closure-consistent):

| marker | x_bar (%/yr) | b_target | R10 eps-path* | var/cur 2050 | var/cur 2100 |
|---|---:|---:|---:|---:|---:|
| ssp119 | 3.01 | 0.696 | 0.18 | 0.964 | 0.958 |
| ssp126 | 3.01 | 0.696 | 0.19 | 0.964 | 0.958 |
| ssp245 | 2.54 | 0.696 | 0.34 | 0.975 | 0.951 |
| ssp370 | 1.11 | 0.696 | 0.56 | 0.990 | 0.944 |
| ssp585 | 3.65 | 0.696 | 0.38 | 0.959 | 0.979 |

\* Ratio of cumulative log changes in regional per-capita final energy and
income, 2023-2100. Scenario-path association, not a structural elasticity.

With b_target growth-adjusted per footnote 3, -(theta + eta x_bar)/kappa:

| marker | b_target | var/cur 2100 |
|---|---:|---:|
| ssp119 | 0.866 | 0.872 |
| ssp126 | 0.866 | 0.872 |
| ssp245 | 0.839 | 0.894 |
| ssp370 | 0.758 | 0.929 |
| ssp585 | 0.902 | 0.866 |

## Findings

1. **The coherence-test prediction is confirmed numerically.** The current
   construction cannot approach its own source paper's long-run response;
   the gap to the benchmark is permanent, not transitional.

2. **Under closure-consistent recalibration, the horizon correction is
   small for the endpoint**: 2100 final energy moves to 0.87-0.98 of the
   current path across markers and b_target modes. The dynamics change the
   defended marginal response and the path shape more than the terminal
   level, because R re-absorbs the shared regional income component.

3. **The decade time effects cancel exactly under recalibrated R.**
   Applying the paper's -0.021 to -0.029/yr decade effects to both Nigeria
   and the region leaves every output row unchanged (identical to the
   delta-off run). This is the cleanest demonstration yet of what the
   residual absorbs: any common additive time trend is divided out, and
   decade effects matter only if they are Nigeria-specific or if R is held
   fixed.

4. **The residual convention dominates.** The conditional experiment with R
   frozen at the old law (fixed-old) plus decade effects puts 2100 demand
   at 0.41-0.48 of current. That spread is a statement about the modelling
   convention, not about Nigeria: it shows the elasticity-horizon debate is
   second-order relative to how R is defined and whether time trends are
   shared between the country and the region.

5. **The IMAGE R10 embedded income response, as a scenario-path proxy, is
   0.18-0.56 depending on marker** -- well below the 0.48-0.62 law used to
   strip income out of the regional path, and far below the paper's 0.70
   long-run value. If the regional model's structural income response is
   genuinely lower, the recalibration over-removes the income effect and
   the residual R carries a negative income artifact alongside its
   efficiency content. The SSP1 values (0.18-0.19) come from
   mitigation-conditioned markers (SPA scenarios), so at least part of the
   low reading is policy, not structure. This number remains the single
   most consequential unverified quantity in the architecture; the proper
   next step is ceteris-paribus income perturbations on the IMAGE inputs,
   not regression on the scenario path.

## Limits of this experiment

- Table 5 "total" is a primary-energy elasticity applied to a final-energy
  anchor; the variant inherits the mismatch and does not resolve it.
- The ETA interaction is evaluated with the baseline's own approximation
  (Nigeria 2023 mapped to the paper's 25th-percentile deviation, -0.923 log
  units); income-unit conversion between USD_2015 PPP and the paper's 2005
  PPP demeaned sample is not performed.
- LAMBDA = -kappa is an annual linearisation of a decade-sampled estimate;
  validated against the decade recursion only in Test 1 (gap ~0.004 log
  points after 2033).
- The region is run through the same law with the same anchor deviation,
  mirroring the baseline's symmetric assumption; R10's true position in the
  paper's income distribution is unmeasured.
- The fixed-old run is a conditional experiment under an independent
  structural assumption about R, not a confidence interval.
