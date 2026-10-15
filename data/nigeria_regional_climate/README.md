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

From the repository root (network required):

```
python scripts/fetch_regional_climate.py --config config.yaml
```

Standard library plus PyYAML; overwrites the CSVs in this folder. The period, pathways and output
names are under `regional_climate` in `config.yaml`; the Admin-1 code → state → zone map is
`admin1_units.yaml` in this folder. The three zone CSVs can be re-derived offline from the two
Admin-1 CSVs (`src/regional_climate/zones.py`; checked by `tests/test_regional_climate.py`). The
script writes CRLF line endings; the committed CSVs are stored with LF.

## State boundaries

`geoBoundaries-NGA-ADM1_simplified.geojson` draws the prototype's zone maps; no model figure is computed
from it (the 2026-10 audit in `docs/zone_boundaries_review.md` used it).

- **Source:** GRID3 Nigeria state boundaries (boundary year 2022), redistributed by geoBoundaries
  gbOpen as `NGA-ADM1-27671186` (build 2023-12-12), simplified release; identifier, build date and
  licence from the geoBoundaries `geoBoundaries-NGA-ADM1-metaData.json` beside the file
- **Licence:** Creative Commons Attribution 4.0 (CC BY 4.0)
- **URL:** https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/main/releaseData/gbOpen/NGA/ADM1/geoBoundaries-NGA-ADM1_simplified.geojson
- **Retrieved:** 2026-10-15; SHA-256 `edd28050c7f1ae40471424605f74e4d2df83502e4f301089761ae18f8ae2fbbf`
- **Join:** `shapeISO` (ISO 3166-2) to `iso3166_2` in `admin1_units.yaml`; the file's names differ
  from CCKP's ("Abuja Federal Capital Territory", "Nasarawa" against "Abuja", "Nassarawa").
- **Mismatch:** CCKP computes the state values on its own Admin-1 boundaries, not these; the size of
  the difference has not been measured [GAP].

Rebuild the maps with `python scripts/build_zone_map.py --config config.yaml`.

## Files

| File | Contents |
|---|---|
| `cckp_cmip6_nigeria_ensemble_2080-2099.csv` | National ensemble median, 10th and 90th percentile, per pathway |
| `cckp_cmip6_admin1_anomalies_2080-2099.csv` | Ensemble values for the 36 states and the FCT, with zone |
| `cckp_cmip6_model_admin1_anomalies_2080-2099.csv` | Individual-model state values |
| `cckp_cmip6_model_geopolitical_zone_2080-2099.csv` | One value per model and zone (median of its states), with the number of states each median uses (`temperature_state_count`, `precipitation_state_count`; 0 where CCKP gave no value, as for kiost-esm precipitation) |
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
