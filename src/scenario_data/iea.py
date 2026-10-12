"""Read IEA Energy Statistics Data Browser exports."""

from __future__ import annotations

import csv
from collections.abc import Container
from pathlib import Path


def read_label_values(path: Path) -> dict[str, float]:
    """A two-column export (label, value); rows with an empty value are skipped."""

    out = {}
    with path.open(encoding="utf-8-sig") as fh:
        for r in list(csv.reader(fh))[1:]:
            if len(r) >= 2 and r[1].strip():
                out[r[0]] = float(r[1])
    return out


def read_year_totals(path: Path, label_filter: Container[str] | None = None) -> dict[int, float]:
    """A (label, value, year) export summed over labels per year, optionally filtered."""

    out: dict[int, float] = {}
    with path.open(encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))
    for r in rows[1:]:
        if len(r) < 3 or not r[1].strip():
            continue
        if label_filter and r[0] not in label_filter:
            continue
        out[int(r[2])] = out.get(int(r[2]), 0.0) + float(r[1])
    return out
