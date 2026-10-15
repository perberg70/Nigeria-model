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
  state → ISO 3166-2 code → zone).
- `zone_geometry.py` – draws the prototype's zone maps from real state boundaries (offline;
  `scripts/build_zone_map.py`).

## Zone maps

The prototype's two regional maps draw each zone as its member states, from GRID3 2022 state
boundaries (`regional_climate.state_boundaries`), joined to the unit file on ISO 3166-2 code.
States are projected equirectangularly (x scaled by the cosine of the mid-latitude) and each
shared border is simplified once (Douglas–Peucker, `boundary_simplify_deg`), so neighbouring
states keep identical edges. Borders between zones and the national outline are drawn heavier;
state borders are thin. `tests/test_regional_climate.py` checks that the spliced block matches
a rebuild and that at least 90% of 0.1° sample points inside each real state fall inside that state's
drawn path (the remainder lie at simplified edges).

Until 2026-10-15 the maps were Voronoi cells around six hand-placed points: 15 of the 37 states were
drawn in the wrong zone, and the drawn South East contained none of the real South East
(feedback from Nigerian researchers). `zone_boundaries_review.md` records the audit.

The boundaries are not CCKP's: CCKP computes the state values on its own Admin-1 boundary set,
and the difference has not been measured [GAP]. The drawing does not affect any number.

## Configuration (`config.yaml`)

`regional_climate` (period, pathways, model pathways, percentiles, unit file, output names,
request settings; state boundary file, simplification tolerance, source label and prototype
path for the zone maps) and `region.iso3`.

## Outputs

Six CSVs in `data/nigeria_regional_climate/` (see its README). The model-zone CSV carries
`temperature_state_count` and `precipitation_state_count`: the states each median actually uses
(`state_count` is the zone's size). A model run CCKP returns without data is logged as a dropped
run; a configured model pathway CCKP lists no runs for is an error.
