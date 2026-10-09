# Nigeria energy statistics — UN Statistics Division, 2020–2023

Nigeria's energy statistics from the UNSD energy database (built from national questionnaire
submissions).

- **API endpoint:** `https://data.un.org/WS/rest/data/UNSD,DF_UNDATA_ENERGY/`
- **Dataflow:** `UNSD:DF_UNDATA_ENERGY(1.2)`, structure `DSD_ENERGY`.
- **Retrieved:** 2026-08-30. No API key needed.
- **Licence:** check UNSD's terms before reuse.

## File

`unsd_nigeria_energy_2020_2023.csv` — the API response as returned: 899 observations, all
commodities and transactions, 2020–2023. Columns: `REF_AREA` (566 = Nigeria), `COMMODITY`,
`TRANSACTION`, `TIME_PERIOD`, `OBS_VALUE`, `UNIT_MEASURE`, `OBS_STATUS`.

## Reproduce

```
curl -H "Accept: application/vnd.sdmx.data+csv" \
  "https://data.un.org/WS/rest/data/UNSD,DF_UNDATA_ENERGY/A.566...?startPeriod=2020&endPeriod=2023&dimensionAtObservation=AllDimensions"
```

Code lists: `https://data.un.org/WS/rest/datastructure/UNSD/DSD_ENERGY/?references=all`

## Codes used

| Code | Meaning |
|---|---|
| `01` | Production |
| `015CE` / `016CE` | Electricity from combustible fuels — main activity / autoproducer |
| `015HY` / `016HY` | Hydro — main activity / autoproducer |
| `015SP` / `016SP` | Solar PV — main activity / autoproducer |
| `088`, `08811` / `08812` | Transformation in electricity plants — total, main activity / autoproducer |
| `13341` / `13342` | Installed capacity, combustible fuels — main activity / autoproducer |

Commodity `7000` = electricity (GWh); `3000` = natural gas (TJ); `4xxx` = oil products.

## Findings, 2023

- Electricity output totals 40,959.6 GWh (combustible fuels 31,640.8, hydro 9,107.2, solar 211.6),
  matching the IEA's older release (40,958 GWh). The current release (28 Sep 2026), which the
  prototype now uses, differs from UNSD by gas −40, solar +55 and total +15 GWh.
- All fuel input to electricity generation is natural gas (327,326 TJ). **No oil product is
  reported as input to electricity generation in any year 2020–2023** — back-up diesel and petrol
  generators are not in the reported electricity statistics.
- Installed capacity: 14,202.8 MW.

## Caveat

The split between main-activity and autoproducer plants is unreliable (it reverses in 2021, and the
implied capacity factors are implausible). Use totals only.
