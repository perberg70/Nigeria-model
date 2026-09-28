# Nigeria hot days — World Bank CCKP, CMIP6

Days per year above 35 °C and 40 °C, and annual mean temperature, for Nigeria.

- **Source:** World Bank Climate Change Knowledge Portal data API, https://cckpapi.worldbank.org/cckp/v1/
- **Collection:** `cmip6-x0.25`, multi-model ensemble.
- **Retrieved:** 2026-08-07.
- **Licence:** check the World Bank's terms before reuse.

## File

`hot_days_nigeria.csv`:

| Variable | Meaning | Coverage |
|---|---|---|
| `hd35` | Days per year with daily maximum above 35 °C | Historical 1995–2014; four SSPs at 2080–2099 (median, 10th, 90th percentile) and 2040–2059; SSP1-1.9 |
| `hd40` | Same for 40 °C | Historical and four SSPs at 2080–2099 |
| `tas` | Annual mean near-surface temperature, °C | Historical and four SSPs at 2080–2099 |

## Query format

```
https://cckpapi.worldbank.org/cckp/v1/{collection}_{type}_{variable}_{product}_{aggregation}_{period}_{percentile}_{scenario}_{model}_{model-calculation}_{statistic}/NGA?_format=json
```

Example:

```
https://cckpapi.worldbank.org/cckp/v1/cmip6-x0.25_climatology_hd35_climatology_annual_2080-2099_median_ssp245_ensemble_all_mean/NGA?_format=json
→ {"data":{"NGA":{"2080-07":163.9}}}
```

The historical baseline uses `historical` as scenario and `1995-2014` as period.

## Notes

- Under SSP2-4.5 the ensemble spans 123 to 206 hot days (median 164) — wider than the median
  difference between SSP1-2.6 (133) and SSP5-8.5 (224). Climate-model choice matters more than
  the emissions pathway for this indicator.
- The projection window is 2080–2099; a 2081–2100 query returns no data.
- CCKP's warming is 0.25–0.39 °C higher than the prototype's FaIR-based national warming in every
  pathway; both are shown, neither adjusted.
