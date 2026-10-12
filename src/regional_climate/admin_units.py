"""The Admin-1 units of the configured country and the zones they aggregate to."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class AdminUnit:
    code: str
    state: str
    zone: str


def load_admin_units(path: Path) -> list[AdminUnit]:
    """Read ``admin1_units`` from a YAML data file, in file order."""

    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    units = [AdminUnit(**{k: str(v) for k, v in row.items()}) for row in data["admin1_units"]]
    codes = [u.code for u in units]
    if len(set(codes)) != len(codes):
        raise ValueError(f"{path}: duplicate Admin-1 codes")
    return units
