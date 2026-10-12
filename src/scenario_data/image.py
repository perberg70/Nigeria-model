"""Read Scenario Compass IMAGE exports keyed by (model, scenario) pairs."""

from __future__ import annotations

import csv
from collections.abc import Mapping
from pathlib import Path

ScenarioKey = tuple[str, str]
"""``(model, scenario)``: the identity of an IAM scenario. Never the scenario name alone."""


def read_series(image_dir: Path, filename: str) -> dict[ScenarioKey, dict[int, float]]:
    """One Scenario Compass variable file as ``{(model, scenario): {year: value}}``."""

    out: dict[ScenarioKey, dict[int, float]] = {}
    with (image_dir / filename).open(encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            key = (r["Model name"], r["Scenario name"])
            out.setdefault(key, {})[int(r["year"])] = float(r["value"])
    return out


def interp(y: float, d: Mapping[int, float]) -> float:
    """Linear interpolation on a dict {year: value}; clamped at both ends."""

    ys = sorted(d)
    if y <= ys[0]:
        return d[ys[0]]
    if y >= ys[-1]:
        return d[ys[-1]]
    for a, b in zip(ys, ys[1:], strict=False):
        if a <= y <= b:
            return d[a] + (d[b] - d[a]) * (y - a) / (b - a)
    raise ValueError(f"cannot interpolate year {y}")
