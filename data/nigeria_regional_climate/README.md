# Nigeria regional climate projections — World Bank CCKP, CMIP6

State and zone-level temperature and rainfall change for Nigeria, 2080–2099 against 1995–2014.

- **Provider:** World Bank Climate Change Knowledge Portal (CCKP)
- **Collection:** `cmip6-x0.25` (bias-corrected, downscaled CMIP6 at 0.25°)
- **Documentation:** https://climateknowledgeportal.worldbank.org/download-data and
  https://worldbank.github.io/climateknowledgeportal/docs/collections/cmip6-x0.25.html
- **Variables:** annual mean temperature anomaly (`tas`), annual precipitation anomaly (`pr`)
- **Pathways:** SSP1-1.9, SSP1-2.6, SSP2-4.5, SSP3-7.0, SSP5-8.5
- **Retrieved:** 2026-08-21 and 2026-08-22.

## Reproduce

From the repository root:

```
python scripts/fetch_nigeria_regional_climate.py
```

Standard library only; overwrites the CSVs in this folder.

## Files

| File | Contents |
|---|---|
| `cckp_cmip6_nigeria_ensemble_2080-2099.csv` | National ensemble median, 10th and 90th percentile, per pathway |
| `cckp_cmip6_admin1_anomalies_2080-2099.csv` | Ensemble values for the 36 states and the FCT, with zone |
| `cckp_cmip6_model_admin1_anomalies_2080-2099.csv` | Individual-model state values |
| `cckp_cmip6_model_geopolitical_zone_2080-2099.csv` | One value per model and zone (median of its states) |
| `cckp_cmip6_geopolitical_zone_ensemble_2080-2099.csv` | Zone median, 10th and 90th percentile across models, with model counts |
| `cckp_cmip6_geopolitical_zone_summary_2080-2099.csv` | Zone summary of the ensemble state values (median, min, max, state count) |

## Method

The six zones are North Central, North East, North West, South East, South South and South West.
For each model, a zone's value is the unweighted median of its states; the zone's displayed median
and 10th–90th percentiles are taken across models. Not area- or population-weighted, and not an
official CCKP product.

## Caveats

- The 10th–90th percentile range is climate-model spread, not a probability interval.
- CCKP publishes no individual-model output for SSP1-1.9, so that pathway has a median only.
- Annual rainfall change says nothing about seasonality, extremes, drought or flooding.
