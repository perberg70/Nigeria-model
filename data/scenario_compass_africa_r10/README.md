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
| `build_nigeria_baseline.py` | Builds the prototype's Nigeria baseline series from these files and `../iiasa_ssp_nigeria/` |
| `nigeria_baseline_block.js` | Output of the builder; the same block sits in the prototype |

Run `python3 build_nigeria_baseline.py` to regenerate `nigeria_baseline_block.js`, or
`python3 build_nigeria_baseline.py --update-prototype` to also write it into
`../../prototype/africa-prototype.html`.

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

- electrification share of final energy and the low-emission share of electricity (power-sector
  baseline);
- the final-energy-per-GDP trajectory, as an efficiency and structural-change factor in the
  economy-wide CO₂ baseline.

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
