"""Sector-wise energy conversion factors under electrification.

Usage
-----
```bash
python scripts/run_sector_conversion.py --config config.yaml
```

Reads ``sector_conversion`` (efficiency ratios, targets, illustration marker),
the 2023 IEA/UNSD tables under ``inputs``, the ETP cooking extraction and the
generated baseline block (``ssp_baseline.output_block``; run
``scripts/run_ssp_baseline.py`` first after any baseline change). The report
(sections 1-7) is written to ``sector_conversion.report`` and echoed to stdout;
see ``data/scenario_compass_africa_r10/partial_adjustment/SECTOR_CONVERSION.md``.
"""

from __future__ import annotations

import argparse
import sys

import _path_setup  # noqa: F401

from config_paths import add_config_argument, load_config, require_path
from demand_analysis import capture, write_report
from demand_analysis.sector_conversion import SectorConversionParams, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_config_argument(parser)
    args = parser.parse_args()

    config = load_config(args.config)
    text = capture(report, SectorConversionParams.from_config(config))
    write_report(require_path(config, "sector_conversion.report"), text)
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
