"""Fetch Admin-1 CMIP6 anomalies from the World Bank CCKP API and derive zone values.

Usage
-----
```bash
python scripts/fetch_regional_climate.py --config config.yaml
```

NETWORK REQUIRED. Reads ``regional_climate`` (period, pathways, Admin-1 unit
file, output names) and ``region.iso3``. Writes six CSVs to
``regional_climate.output_dir``; see data/nigeria_regional_climate/README.md.
The zone CSVs can be re-derived offline from the two admin-level CSVs with the
functions in ``src/regional_climate/zones.py``.
"""

from __future__ import annotations

import argparse
from datetime import date

import _path_setup  # noqa: F401

from config_paths import add_config_argument, load_config
from regional_climate import (
    FetchSettings,
    derive_model_zone_rows,
    derive_zone_ensemble_rows,
    derive_zone_rows,
    write_csv,
)
from regional_climate.fetch import fetch, fetch_all_model_states, fetch_national


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_config_argument(parser)
    args = parser.parse_args()

    s = FetchSettings.from_config(load_config(args.config))
    out, names = s.output_dir, s.outputs
    state_rows = [row for pathway in s.pathways for row in fetch(s, pathway)]
    national_rows = [row for pathway in s.pathways for row in fetch_national(s, pathway)]
    zone_rows = derive_zone_rows(state_rows)
    model_state_rows = fetch_all_model_states(s)
    model_zone_rows = derive_model_zone_rows(model_state_rows)
    zone_ensemble_rows = derive_zone_ensemble_rows(model_zone_rows)
    write_csv(out / names["admin1"], state_rows)
    write_csv(out / names["zone_summary"], zone_rows)
    write_csv(out / names["national_ensemble"], national_rows)
    write_csv(out / names["model_admin1"], model_state_rows)
    write_csv(out / names["model_zone"], model_zone_rows)
    write_csv(out / names["zone_ensemble"], zone_ensemble_rows)
    print(
        f"Retrieved {date.today().isoformat()}: {len(state_rows)} state rows; "
        f"{len(zone_rows)} zone rows; {len(national_rows)} national ensemble rows; "
        f"{len(model_state_rows)} model-state rows; {len(zone_ensemble_rows)} zonal ensemble rows"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
