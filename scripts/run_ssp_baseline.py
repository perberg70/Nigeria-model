"""Build the SSP baseline block and, optionally, splice it into the prototype.

Usage
-----
```bash
python scripts/run_ssp_baseline.py --config config.yaml [--update-prototype]
```

Reads the ``ssp_baseline`` section (anchors, demand relation, envelope) plus
``scenarios``, ``time_horizon`` and ``inputs``. Writes the generated JavaScript to
``ssp_baseline.output_block``; with ``--update-prototype`` it also copies the
four blocks into ``ssp_baseline.prototype_html``. Self-checks and the envelope
and candidate-rule tables are printed to stdout.
"""

from __future__ import annotations

import argparse
import logging

import _path_setup  # noqa: F401

from config_paths import add_config_argument, load_config
from ssp_baseline import (
    BaselineParams,
    build_baseline,
    print_diagnostics,
    render_block,
    update_prototype_html,
)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_config_argument(parser)
    parser.add_argument(
        "--update-prototype",
        action="store_true",
        help="also copy the generated blocks into the prototype HTML",
    )
    args = parser.parse_args()

    params = BaselineParams.from_config(load_config(args.config))
    result = build_baseline(params)
    print_diagnostics(result)

    text = render_block(result)
    out = params.output_block
    with out.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    if args.update_prototype:
        html_path = params.prototype_html
        html = html_path.read_text(encoding="utf-8")
        with html_path.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(update_prototype_html(html, text))
        print("updated: %s" % html_path)
    print("written: %s  (%d bytes)" % (out, out.stat().st_size))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
