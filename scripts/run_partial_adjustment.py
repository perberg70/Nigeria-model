"""Run the partial-adjustment demand variant and its two coherence tests.

Usage
-----
```bash
python scripts/run_partial_adjustment.py --config config.yaml
```

Reads ``partial_adjustment`` (test design, leg sequence), the Burke & Csereklyei
coefficients under ``parameters`` and the current law under ``ssp_baseline.demand``.
The report is written to ``partial_adjustment.report`` and echoed to stdout;
see ``data/scenario_compass_africa_r10/partial_adjustment/MEMO.md``.
"""

from __future__ import annotations

import argparse
import sys

import _path_setup  # noqa: F401

from config_paths import add_config_argument, load_config, require_path
from demand_analysis import PartialAdjustmentParams, capture, write_report
from demand_analysis.partial_adjustment import report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_config_argument(parser)
    args = parser.parse_args()

    config = load_config(args.config)
    text = capture(report, PartialAdjustmentParams.from_config(config))
    write_report(require_path(config, "partial_adjustment.report"), text)
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
