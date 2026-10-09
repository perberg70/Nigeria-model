# Nigeria population and GDP by SSP — IIASA SSP Database

Population and GDP paths for Nigeria under the Shared Socioeconomic Pathways.

- **Source:** IIASA SSP Scenario Explorer, https://ssp.apps.ece.iiasa.ac.at/
- **Query:** region `Nigeria`; variables `Population` and `GDP|PPP`; historical reference plus
  SSP1, SSP2, SSP3 and SSP5; 1950–2100 in five-year steps.
- **Models:** population from **IIASA-WiC POP 2025**; GDP from **OECD ENV-Growth 2025**
  (2025 releases).
- **Licence:** IIASA publishes the SSP database under CC BY 4.0 for most versions; check the
  terms on the Scenario Explorer before reuse.

## File

`Population_GDP_PPP_IIASA_SSP_15_Nigeria.csv` — the export as downloaded (20 rows):

| Variable | Unit | Historical | Scenarios |
|---|---|---|---|
| `Population` | million | 1950–2025 | SSP1/2/3/5, 2025–2100 |
| `GDP|PPP` | billion USD_2010, USD_2015 and USD_2017 per year | 2010–2025 | SSP1/2/3/5, 2025–2100 |

SSP4 is not included.

## Headline values

Population, million (all scenarios share 2025 = 232.144):

| | 2030 | 2040 | 2050 |
|---|---|---|---|
| SSP1 | 256.76 | 305.79 | 356.55 |
| SSP2 | 261.14 | 327.15 | 400.61 |
| SSP3 | 264.63 | 344.76 | 439.31 |
| SSP5 | 256.74 | 305.61 | 356.03 |

GDP|PPP compound growth 2025–2050 (USD_2015): SSP1 4.80%, SSP2 4.50%, SSP3 3.97%, SSP5 5.42% per
year. The three price bases differ only by a constant, so growth rates are identical.

## How the prototype uses it

Before 2025 every scenario uses the historical reference; from 2025 the scenario's own row.
2023 and 2024 are interpolated linearly between the 2020 and 2025 historical values. Population
scales energy demand and household air-pollution deaths; GDP per head (USD_2015 row) drives the
baseline energy demand and the income effect on clean cooking. For clean cooking it enters the
prototype only through the income index `pollutingIdxSSP`, which `build_nigeria_baseline.py`
generates (since 2026-10-09; before then the prototype held a hand-pasted GDP table).
