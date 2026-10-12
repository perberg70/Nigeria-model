"""Compare Nigeria's carbon intensity with Africa's and with IMAGE's Africa R10.

Usage
-----
```bash
python scripts/run_carbon_intensity.py --config config.yaml [--iea-africa DIR]
```

Reads ``carbon_intensity`` (compared countries, observed window, coal factor,
biomass ratio) and the OWID, IEA, WDI and IMAGE inputs under ``inputs``.
``--iea-africa`` overrides ``inputs.iea_africa_dir`` for the Africa final-energy
rows. The report is written to ``carbon_intensity.report`` and echoed to stdout;
see ``data/scenario_compass_africa_r10/carbon_intensity/MEMO.md``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import _path_setup  # noqa: F401

from config_paths import add_config_argument, load_config, require_path
from demand_analysis import capture, write_report
from demand_analysis.carbon_intensity import CarbonIntensityParams, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_config_argument(parser)
    parser.add_argument(
        "--iea-africa",
        type=Path,
        metavar="DIR",
        help="directory of IEA Africa chart exports (overrides inputs.iea_africa_dir)",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    params = CarbonIntensityParams.from_config(config, iea_africa_override=args.iea_africa)
    text = capture(report, params)
    write_report(require_path(config, "carbon_intensity.report"), text)
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
