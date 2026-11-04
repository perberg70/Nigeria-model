"""Embed the frozen canvas boundary snapshot in the Colombia prototype.

Usage
-----
```bash
python scripts/build_department_map.py --config config.yaml
```

Offline. Reads ``colombia_department_map`` (``boundaries``, ``expected_units``,
``prototype_html``) and replaces the ``DEPARTMENT_MAP`` block in the prototype.
"""

from __future__ import annotations

import argparse
import json
import re

import _path_setup  # noqa: F401

from config_paths import add_config_argument, load_config, require, require_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_config_argument(parser)
    args = parser.parse_args()
    config = load_config(args.config)
    geometry = json.loads(
        require_path(config, "colombia_department_map.boundaries").read_text(encoding="utf-8")
    )
    count = sum(len(units) for units in geometry["regions"].values())
    if count != int(require(config, "colombia_department_map.expected_units")):
        raise ValueError(f"Expected configured boundary count, got {count}")
    path = require_path(config, "colombia_department_map.prototype_html")
    block = (
        "// BEGIN DEPARTMENT_MAP\nconst DEPARTMENT_MAP = "
        + json.dumps(geometry, ensure_ascii=False, separators=(",", ":"))
        + ";\n// END DEPARTMENT_MAP"
    )
    text, replacements = re.subn(
        r"// BEGIN DEPARTMENT_MAP.*?// END DEPARTMENT_MAP",
        lambda _: block,
        path.read_text(encoding="utf-8"),
        flags=re.DOTALL,
    )
    if replacements != 1:
        raise ValueError("Expected exactly one department-map block")
    path.write_text(text, encoding="utf-8")
    print(f"Embedded {count} frozen boundary paths; upstream provenance gap preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
