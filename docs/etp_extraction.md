# ETP Chart Extraction (`src/etp_extraction`)

## Overview

Recovers numeric series from the vector stacked-bar charts of the Energy Transition Plan update
(`etp_extraction.pdf`): every bar segment is a filled rectangle in the PDF content stream.

## Key Components

- `pdf_vectors.py` – content-stream tokenizer, `parse_page()` (filled rectangles and text runs),
  the atomic CSV writer.
- `power.py` (pp.17–18), `demand.py` (p.22), `cooking.py` (pp.37–40), `industry.py`
  (pp.27–29) – one `run(pdf, outdir)` each.

## Configuration (`config.yaml`)

Only the PDF path and the output directory. Page numbers, axis calibration and the prose
figures each chart is validated against are facts about this one document and are kept with
the chart module that reads them.

## Outputs

`etp_*.csv` in `data/seforall_nigeria_etp/`. Validation results and the known differences
between a fresh extraction and the committed CSVs are in that folder's README.
