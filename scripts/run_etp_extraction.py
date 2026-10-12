"""Extract the Energy Transition Plan charts from the PDF into CSVs.

Usage
-----
```bash
python scripts/run_etp_extraction.py --config config.yaml [--chart power demand cooking industry]
                                     [--output-dir DIR]
```

Reads ``etp_extraction.pdf`` and writes to ``etp_extraction.output_dir`` (or
``--output-dir``). Each chart group is validated against the figures the
document states in prose; a group that fails a gating check writes none of its
CSVs and the script exits 1. A fresh extraction matches the committed CSVs except
for line endings (see data/seforall_nigeria_etp/README.md), so use
``--output-dir`` to compare first.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import _path_setup  # noqa: F401

from config_paths import add_config_argument, load_config, require_path
from etp_extraction import CHARTS, ExtractionError


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_config_argument(parser)
    parser.add_argument(
        "--chart",
        nargs="+",
        choices=list(CHARTS),
        default=list(CHARTS),
        help="chart groups to extract (default: all, in this order)",
    )
    parser.add_argument(
        "--output-dir", type=Path, help="write here instead of etp_extraction.output_dir"
    )
    args = parser.parse_args()

    config = load_config(args.config)
    pdf = require_path(config, "etp_extraction.pdf")
    outdir = args.output_dir or require_path(config, "etp_extraction.output_dir")
    outdir.mkdir(parents=True, exist_ok=True)
    for name in args.chart:
        try:
            CHARTS[name].run(pdf, outdir)
        except ExtractionError as exc:
            parser.exit(1, f"{name}: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
