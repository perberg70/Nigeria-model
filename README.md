# Nigeria model

Scripts and data for the Africa (Nigeria) prototype: an interactive decision-support tool that
shows how Nigeria's energy choices affect CO₂ emissions, the social cost of carbon, household
air-pollution deaths and local climate impacts under the Shared Socioeconomic Pathways (SSPs).

## How to use

Open `prototype/africa-prototype.html` in any web browser. It is a single self-contained file:
no installation, server or internet connection is needed. A short header comment in the file
describes its structure; data sources are documented in `data/` and `data_sources/`.

## Contents

| Folder | Contents |
|---|---|
| `prototype/` | The prototype, `africa-prototype.html` |
| `data/` | One folder per dataset, each with a `README.md` describing source, retrieval and processing. Scripts that build derived series sit beside their data |
| `scripts/` | Retrieval script for the regional climate projections |
| `data_sources/` | Index of every external source, with URLs |

## Caveats

- This is a prototype. Its figures are transparent calculations on published data, not the
  output of a validated forecasting model.
- Licences differ by dataset; see `data_sources/README.md` and each data folder's README before
  reusing a file.
