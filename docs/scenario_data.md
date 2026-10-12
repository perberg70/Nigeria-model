# Scenario and Statistics Readers (`src/scenario_data`)

## Overview

Shared readers for the exports every other package uses, consolidated from copies that were
previously duplicated across scripts.

## Key Components

- `image.read_series(image_dir, filename)` – one Scenario Compass variable file as
  `{(model, scenario): {year: value}}`.
- `image.interp(year, series)` – linear interpolation, clamped at both ends.
- `scenarios.load_markers(config)` – the `scenarios` section as `Marker` objects; `Marker.key`
  is the `(model, scenario)` pair.
- `iiasa.IiasaExport` / `country_series()` – the country's own population and GDP|PPP paths:
  the Historical Reference row through `inputs.iiasa.history_end_year`, narrative rows after it,
  and the base and anchor years interpolated into the five-yearly grid. Missing rows raise.
- `iea.read_label_values()` / `iea.read_year_totals()` – IEA Data Browser exports.

## Units and Conventions

IAM scenarios are identified by `(model, scenario)` pairs, never by scenario name alone, so two
models' scenarios of the same name cannot be merged by accident. All 45 IMAGE files held today
contain a single model, `IMAGE 3.2`.

## Configuration (`config.yaml`)

`scenarios` (pathway id → `label`, `model`, `scenario`, `narrative`), `inputs.image_dir`,
`inputs.iiasa`, `inputs.iea`.
