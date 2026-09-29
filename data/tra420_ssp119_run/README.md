# Social cost of carbon and warming for SSP1-1.9 — model run

Output of an integrated assessment model run (TRA420: FaIR climate module with pulse-based social
cost of carbon), used for the prototype's SSP1-1.9 pathway.

- **Run date:** 2026-08-21, default configuration.
- **Valuation:** pulse mode `ssp_only`, base year 2025, Ramsey discounting with pure time
  preference 0.5% and elasticity 1, 76 pulses per pathway.
- **Temperature:** FaIR (AR6 calibration v1.5.0, ECS 3.0 °C), referenced to 1850–1900 and scaled
  to the assessed warming baseline (1.1102 °C over 2004–2023).

## File

`pulse_scc_timeseries_ramsey_discount_ssp119.csv` — the run's output, unmodified: annual social
cost of carbon, discount factor and present-value damage per pulse.

## Results, SSP1-1.9

- Social cost of carbon, PPP USD-2025 per tCO₂, in the emission year: **308 (2025), 322 (2030),
  403 (2050), 760 (2100)**.
- Global warming 2081–2100 against 1995–2014: **0.52 °C**. Nigeria: **0.53 °C** (national pattern
  factor 1.023043). Rainfall **+2.4 mm/yr**.

## Check

The same run reproduced the other four pathways used in the prototype: social cost of carbon and
discount factors exactly, and global temperatures within 0.003 °C (SSP1-2.6 0.893, SSP2-4.5 1.772,
SSP3-7.0 2.739, SSP5-8.5 3.558 °C).

Nigerian values come only from the model's global parts (global temperature, global SCC pulse)
and Nigeria's national pattern-scaling factor; the model has no Nigeria energy configuration.
