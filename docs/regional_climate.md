# Regional Climate (`src/regional_climate`)

## Overview

Fetches CMIP6 temperature and precipitation anomalies for the configured country's Admin-1
units from the World Bank Climate Change Knowledge Portal and aggregates them to the
prototype's zones. The aggregation is a median of the constituent state values, with the state
minimum and maximum retained; it is not an area-weighted zonal product.

## Key Components

- `fetch.py` – API retrieval (network); `FetchSettings.from_config()`.
- `zones.py` – `derive_zone_rows`, `derive_model_zone_rows`, `derive_zone_ensemble_rows`
  (offline; tested against the committed CSVs).
- `admin_units.py` – reads `data/nigeria_regional_climate/admin1_units.yaml` (CCKP code →
  state → zone).

## Configuration (`config.yaml`)

`regional_climate` (period, pathways, model pathways, percentiles, unit file, output names,
request settings) and `region.iso3`.

## Outputs

Six CSVs in `data/nigeria_regional_climate/` (see its README).
