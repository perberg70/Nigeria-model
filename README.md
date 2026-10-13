# Nigeria model

Scripts and data for the Africa (Nigeria) prototype: an interactive decision-support tool that
shows how Nigeria's energy choices affect CO₂ emissions, the social cost of carbon, household
air-pollution deaths and local climate impacts under the Shared Socioeconomic Pathways (SSPs).

## How to use the prototype

Open `prototype/africa-prototype.html` in any web browser. It is a single self-contained file:
no installation, server or internet connection is needed. A short header comment in the file
describes its structure; data sources are documented in `data/` and `data_sources/`.

## Browser link for external users

The GitHub Pages workflow in `.github/workflows/deploy-pages.yml` publishes a small
landing page and the Nigeria prototype. It copies only `site/index.html` and
`prototype/africa-prototype.html` into the public site artifact; the repository's
research data and scripts are not part of the website.

To activate it, push these files to `main`, then in the GitHub repository open
**Settings → Pages** and set **Build and deployment → Source** to **GitHub Actions**.
Under **Actions**, check that **Publish prototypes** completes successfully. The
browser links will be:

- Landing page: `https://perberg70.github.io/Nigeria-model/`
- Nigeria model: `https://perberg70.github.io/Nigeria-model/nigeria/`

These links are public. Check the embedded model content and source-data licences
before enabling Pages. For a future model, add its HTML file to the repository,
copy it into another folder under `_site` in the workflow, add a link to
`site/index.html`, and include the new source path in the workflow's `push.paths`.

The Python code in this repository builds and checks the data behind the prototype. It follows
the layout and tooling of the TRA420 Western Balkans model (`TRA420_Modeling_2025`).

## Repository Structure

| Path | Contents |
|---|---|
| `prototype/` | The prototype, `africa-prototype.html` |
| `config.yaml` | Every modelling value the scripts use, with its source; all scripts require `--config` |
| `src/` | Library packages (one doc each in `docs/`): `scenario_data`, `ssp_baseline`, `demand_analysis`, `etp_extraction`, `regional_climate`, plus `config_paths.py` and `units.py` |
| `scripts/` | Thin command-line entry points (`run_*.py`, `fetch_regional_climate.py`) |
| `tests/` | Regression tests against the committed outputs, and unit tests |
| `data/` | One folder per dataset, each with a `README.md` describing source, retrieval and processing. Generated outputs (the baseline block, analysis reports, ETP CSVs) and their research memos sit beside the data they come from |
| `data_sources/` | Index of every external source, with URLs |
| `docs/` | Module documentation and the script overview (`docs/scripts.md`) |
| `AGENTS.md`, `CLAUDE.md`, `.claude/agents/`, `.codex/` | Instructions and review checklists for coding agents |

## Getting Started

```bash
conda env create -f environment.yaml
conda activate nigeria-model
pip install -e '.[dev]'
```

`environment.yaml` is the canonical environment; `pyproject.toml` lists the direct
dependencies (`pypdf`, `pyyaml`; `pytest` for development). The scripts also run without
installation: each one adds `src/` to the import path through `scripts/_path_setup.py`.

## Running the Scripts

Run from the repository root; every script requires `--config`:

```bash
python scripts/run_ssp_baseline.py --config config.yaml --update-prototype
python scripts/run_partial_adjustment.py --config config.yaml
python scripts/run_conversion_factors.py --config config.yaml
python scripts/run_sector_conversion.py --config config.yaml
python scripts/run_carbon_intensity.py --config config.yaml
python scripts/run_etp_extraction.py --config config.yaml --output-dir /tmp/etp
python scripts/fetch_regional_climate.py --config config.yaml        # network required
```

What each script reads and writes is in `docs/scripts.md`. `run_sector_conversion.py` reads the
generated baseline block, so run `run_ssp_baseline.py` first after any baseline change.

## Testing

```bash
pytest --basetemp=./.pytest_tmp -m "not network"
```

The regression tests regenerate the four analysis reports, the baseline block and the prototype
splice from `config.yaml` and require them to equal the committed files byte for byte; a change
that moves any committed output must update that output in the same commit.

## Development Guidelines

- **Configuration over constants**: modelling values (anchors, elasticities, coefficients,
  envelopes, comparison countries) live in `config.yaml` with their source and any
  `GAP` / `ASSUMED` / `TRANSFERRED` note. Read them with `config_paths.require()`, which names a
  missing key instead of substituting a default.
- **Region-agnostic code**: Python logic must not branch on country or region names; codes and
  region-specific data belong in `config.yaml` or data files (e.g.
  `data/nigeria_regional_climate/admin1_units.yaml`). Report labels may name countries.
- **Scenario identity**: IAM scenarios are identified by `(model, scenario)` pairs
  (`scenario_data.Marker.key`).
- **Gap flagging**: proxied, transferred or assumed values are marked where they are configured
  and where they are reported, never filled in silently.
- **Generated files**: the baseline block, the prototype's four spliced blocks, the analysis
  reports and the ETP CSVs are outputs; regenerate them with the scripts, do not hand-edit them.
  See `docs/ssp_baseline.md` for which prototype blocks are generated and which are hand-pasted.

## Ruff Linting & Formatting

Ruff settings are identical to TRA420's (`pyproject.toml`: Python 3.11 target, line length 100,
rules `E`, `F`, `I`, `B`, `SIM`; double quotes). Install the Git hooks once per clone:

```bash
pre-commit install
```

and run them on demand with `pre-commit run -a` (ruff-pre-commit v0.6.9: `ruff --fix
--unsafe-fixes` and `ruff-format`). Manually:

```bash
ruff check . --fix
ruff format .
```

## Configuration Overview

`config.yaml` is organised like TRA420's: shared sections first (`region`, `time_horizon`,
`scenarios`, `inputs`, `parameters`), then one section per package (`ssp_baseline`,
`partial_adjustment`, `conversion_factors`, `sector_conversion`, `carbon_intensity`,
`etp_extraction`, `regional_climate`). Relative paths resolve against the config file's
directory.

## Caveats

- This is a prototype. Its figures are transparent calculations on published data, not the
  output of a validated forecasting model.
- Licences differ by dataset; see `data_sources/README.md` and each data folder's README before
  reusing a file.
