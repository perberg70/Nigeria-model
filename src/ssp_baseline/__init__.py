"""SSP baseline for the prototype: emissions, electrification, power mix, population."""

from .builder import (
    BaselineParams,
    BaselineResult,
    apply_envelope,
    build_baseline,
    check_iea_anchors,
    cook_index,
    print_diagnostics,
)
from .js_block import block_series, block_years, render_block
from .prototype import replace_fragment, update_prototype_html, write_prototype

__all__ = [
    "BaselineParams",
    "BaselineResult",
    "apply_envelope",
    "block_series",
    "block_years",
    "build_baseline",
    "check_iea_anchors",
    "cook_index",
    "print_diagnostics",
    "render_block",
    "replace_fragment",
    "update_prototype_html",
    "write_prototype",
]
