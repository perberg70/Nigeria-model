# CLI Scripts Overview

Every script is run from the repository root, requires `--config <file>` (normally
`config.yaml`) and exits with status 2 if it is missing. Paths below are the values in
`config.yaml`.

## SSP baseline

- `scripts/run_ssp_baseline.py --config config.yaml [--update-prototype]`
  - Reads `ssp_baseline`, `scenarios`, `time_horizon`, `inputs.image_dir`, `inputs.iiasa`,
    `inputs.iea` and `inputs.iea_generation_lines` (anchor cross-check).
  - Writes `data/scenario_compass_africa_r10/nigeria_baseline_block.js`; with
    `--update-prototype` also splices its four blocks into `prototype/africa-prototype.html`.
  - Prints self-checks, the resource envelope at its caps and the four candidate fossil-split
    rules to stdout.

## Demand analyses

Each writes its report to the path under `<section>.report` and echoes it to stdout.

- `scripts/run_partial_adjustment.py` → `data/scenario_compass_africa_r10/partial_adjustment/output.txt`
- `scripts/run_conversion_factors.py` → `.../partial_adjustment/conversion_factors_output.txt`
- `scripts/run_sector_conversion.py` → `.../partial_adjustment/sector_conversion_output.txt`
  (reads the generated baseline block; run the baseline first after a baseline change)
- `scripts/run_carbon_intensity.py [--iea-africa DIR]` →
  `data/scenario_compass_africa_r10/carbon_intensity/carbon_intensity_output.txt`
  (`--iea-africa` overrides `inputs.iea_africa_dir`)

## ETP chart extraction

- `scripts/run_etp_extraction.py --config config.yaml [--chart power demand cooking industry] [--output-dir DIR]`
  - Reads `etp_extraction.pdf`; writes `etp_*.csv` to `etp_extraction.output_dir` or `--output-dir`.
  - A failed gating check writes nothing and exits 1. A fresh extraction does not reproduce every
    committed CSV byte for byte (see `data/seforall_nigeria_etp/README.md`), so extract to a
    scratch `--output-dir` and compare before overwriting the committed files.

## Regional climate

- `scripts/fetch_regional_climate.py --config config.yaml` (network required)
  - Reads `regional_climate` and `region.iso3`; writes six CSVs to
    `data/nigeria_regional_climate/`.

## Cleanup Utilities

- `python clean_cache.py` removes `__pycache__`, `.pytest_cache`, `.coverage` and `.ruff_cache`.
