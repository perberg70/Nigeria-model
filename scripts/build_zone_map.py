"""Draw the prototype's six-zone maps from the state boundary file and splice them in.

Usage
-----
```bash
python scripts/build_zone_map.py --config config.yaml
```

Offline. Reads ``regional_climate`` (``admin_units``, ``state_boundaries``,
``boundary_source_label``, ``boundary_simplify_deg``, ``prototype_html``) and replaces the
``NIGERIA_ZONE_MAP`` statement in the prototype. The zone values the maps colour are
spliced separately (hand-pasted ``regionalClimate``; see docs/ssp_baseline.md).
"""

from __future__ import annotations

import argparse

import _path_setup  # noqa: F401

from config_paths import add_config_argument, load_config, require, require_path
from regional_climate import load_admin_units
from regional_climate.zone_geometry import (
    build_zone_map,
    load_state_rings,
    render_js,
    splice_zone_map,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_config_argument(parser)
    args = parser.parse_args()

    config = load_config(args.config)
    units = load_admin_units(require_path(config, "regional_climate.admin_units"))
    rings = load_state_rings(require_path(config, "regional_climate.state_boundaries"), units)
    zone_map = build_zone_map(
        rings,
        {u.state: u.zone for u in units},
        float(require(config, "regional_climate.boundary_simplify_deg")),
    )
    block = render_js(zone_map, str(require(config, "regional_climate.boundary_source_label")))
    html_path = require_path(config, "regional_climate.prototype_html")
    html = splice_zone_map(html_path.read_text(encoding="utf-8"), block)
    with html_path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(html)
    print(
        f"Spliced {len(zone_map.states)} state paths ({len(block):,} characters) into {html_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
