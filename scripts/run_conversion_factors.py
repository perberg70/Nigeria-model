"""Quantify the unit and time-scale conversions behind the partial-adjustment variant.

Usage
-----
```bash
python scripts/run_conversion_factors.py --config config.yaml
```

Reads ``conversion_factors`` (PWT 7.1 values, region-mix marker) plus everything
the partial-adjustment variant reads. The report (sections A-D) is written to
``conversion_factors.report`` and echoed to stdout; see
``data/scenario_compass_africa_r10/partial_adjustment/CONVERSION_FACTORS.md``.
"""

from __future__ import annotations

import argparse
import sys

import _path_setup  # noqa: F401

from config_paths import add_config_argument, load_config, require_path
from demand_analysis import capture, write_report
from demand_analysis.conversion_factors import ConversionFactorsParams, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_config_argument(parser)
    args = parser.parse_args()

    config = load_config(args.config)
    text = capture(report, ConversionFactorsParams.from_config(config))
    write_report(require_path(config, "conversion_factors.report"), text)
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
