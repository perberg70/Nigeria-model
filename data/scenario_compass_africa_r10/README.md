# Africa (R10) SSP scenarios — IMAGE 3.2, SSP2021

Regional energy and emissions scenarios used for the prototype's no-policy baselines.

- **Source:** Scenario Compass, https://scenariocompass.org/scenario-dashboard
- **Region:** Africa (R10). **Model:** IMAGE 3.2. **Project:** SSP2021.
- **Downloaded:** 2026-09-07, with no temperature filter (a filter would drop SSP3-7.0 and
  SSP5-8.5).

## Files

| File | Contents |
|---|---|
| `image32_ssp2021/` | One CSV per variable (filename = IAMC variable name), IMAGE 3.2, five CMIP6 marker scenarios |
| `scenario_metadata.csv` | Scenario-level metadata (climate category, vetting), one row per marker |
| `nigeria_baseline_block.js` | Output of the builder (`src/ssp_baseline/`): four blocks (emissions baseline, power-sector baseline, population, and the clean-cooking income index `pollutingIdxSSP`), copied into the prototype by `--update-prototype` |

The builder reads these files and `../iiasa_ssp_nigeria/`, with every anchor and parameter under
`ssp_baseline` in `config.yaml`. From the repository root, run
`python scripts/run_ssp_baseline.py --config config.yaml` to regenerate
`nigeria_baseline_block.js`, or add `--update-prototype` to also write it into
`prototype/africa-prototype.html`.

## The five marker scenarios

| Marker | Scenario name in the files |
|---|---|
| SSP1-1.9 | `SSP2021-SSP1-SPA1-19-Default` |
| SSP1-2.6 | `SSP2021-SSP1-SPA1-26-Default` |
| SSP2-4.5 | `SSP2021-SSP2-SPA2-45-Default` |
| SSP3-7.0 | `SSP2021-SSP3-Baseline` |
| SSP5-8.5 | `SSP2021-SSP5-Baseline` |

`SSP2021-SSP1-Baseline` is a different, high-warming scenario — not SSP1-1.9.

## Units and years

Energy EJ/yr; emissions Mt CO₂/yr; population million; GDP billion USD_2010/yr. Years 2010, 2015,
2020, then five-year steps to 2100 — there is no 2023. The 2020 base is identical across markers.

## How the prototype uses it

Nigeria is not in this dataset, so only **relative changes** are transferred, anchored to
Nigeria's own observed values:

- the low-emission share of electricity (power-sector baseline);
- an **electrification residual** (power-sector baseline, since 2026-10-22): R10's electrification
  share index (`Secondary Energy|Electricity / Final Energy`, relative to 2023) divided by what
  R10's own income per head gives through the share law `0.30L − 0.09L²`. That law is Burke &
  Csereklyei's electricity law (Table 6 col. 6, `0.66L − 0.025L²`) less the total-energy law below.
  Nigeria's share is its 2023 value times the same law on Nigeria's own income times this residual
  (`r10_electrification()` in `src/ssp_baseline/builder.py`). R10's raw share index was used until
  then; it carried R10's faster income growth into Nigeria's share. The law explains only a quarter
  to two-fifths of R10's share growth to 2050, so the residual carries most of it, including any
  income response IMAGE has beyond the law. Past the law's peak, the residual rises as R10's income
  grows (gap notes in `config.yaml`);
- an **efficiency residual**, as an efficiency, structure and fuel-switching factor in the
  economy-wide CO₂ baseline and in final-energy demand (baseline and the user's pathway). It is
  R10's final-energy path divided by what R10's own population and income per head give through the
  same Burke & Csereklyei relation the prototype applies to Nigeria (`0.36L + 0.065L²`):
  `T(y) = [FE(y)/FE(ref)] / [P(y)/P(ref) × exp(0.36L + 0.065L²)]`, `L = ln(GDPpc(y)/GDPpc(ref))`,
  with `ref` 2023 for final energy and 2024 for CO₂ (`r10_efficiency()` in
  `src/ssp_baseline/builder.py`). The raw `Final Energy/GDP` ratio was used until 2026-10-03; it
  counted the income effect twice. The residual can exceed 1 (SSP3-7.0 and SSP5-8.5 in 2050),
  meaning energy per unit of output rises once the income effect is removed.

Nigeria's population and GDP come from `../iiasa_ssp_nigeria/`, not from this region.

## Caveats

- The export contains no region column; the region is known from the download settings. The
  2020 population (1,325.9 million) matches the whole of Africa.
- In the SSP1 scenarios the by-fuel generation series exceed the reported electricity total
  (by 1.6% in 2050 and 32.9% in 2100 for SSP1-1.9); shares are therefore computed from the sum of
  the by-fuel rows.
- `Primary Energy - Biomass.csv` lacks `SSP2021-SSP3-Baseline`.
- Residential solids reconcile exactly: coal + biomass = solids; biomass is 99.1% of residential
  solids in 2020.
