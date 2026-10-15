# Project Documentation

Module-level documentation for the Nigeria model. Each document covers one package under `src/`
and lists its inputs, equations, configuration and outputs; research findings stay in the memos
beside the data (`data/**/MEMO.md`, `CONVERSION_FACTORS.md`, `SECTOR_CONVERSION.md`).

- `scripts.md` – every command-line script, what it reads and what it writes.
- `scenario_data.md` – readers for the IMAGE, IIASA and IEA exports; scenario identity.
- `ssp_baseline.md` – the SSP baseline behind the prototype and the prototype splice, including
  which prototype blocks are generated and which are hand-pasted.
- `demand_analysis.md` – partial adjustment, conversion factors, sector conversion and carbon
  intensity (exploratory comparators; none changes the baseline).
- `etp_extraction.md` – reading the Energy Transition Plan's vector charts.
- `regional_climate.md` – CCKP Admin-1 climate anomalies, the six-zone aggregation and the zone maps.
- `zone_boundaries_review.md` – audit of the earlier zone-map borders (2026-10), with the
  assumptions behind the regional climate figures.
