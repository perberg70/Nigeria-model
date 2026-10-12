"""Exploratory analyses of the demand law: partial adjustment, conversion factors,
sector conversion under electrification, and carbon intensity."""

from .partial_adjustment import (
    PartialAdjustmentParams,
    decade_recursion,
    growth_adjusted_b,
    pa_path,
)
from .reporting import capture, write_report
from .table5 import CurrentLaw, Table5Column, load_current_law, load_table5

__all__ = [
    "CurrentLaw",
    "PartialAdjustmentParams",
    "Table5Column",
    "capture",
    "decade_recursion",
    "growth_adjusted_b",
    "load_current_law",
    "load_table5",
    "pa_path",
    "write_report",
]
