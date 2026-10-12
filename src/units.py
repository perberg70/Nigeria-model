"""Methodological unit constants (exact definitions, not data)."""

from __future__ import annotations

TJ_PER_GWH = 3.6  # 1 GWh = 3.6 TJ
HOURS_PER_YEAR = 8760
MJ_PER_KGOE = 41.868  # IEA: 1 toe = 41.868 GJ
KWH_PER_GJ = 1 / 3.6e-3  # 1 GJ = 277.8 kWh

__all__ = ["HOURS_PER_YEAR", "KWH_PER_GJ", "MJ_PER_KGOE", "TJ_PER_GWH"]
