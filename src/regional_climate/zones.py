"""Aggregate CCKP Admin-1 anomalies to the prototype's zones (offline, no network).

The prototype aggregation is deliberately a median of the constituent
state-level aggregates, with the state minimum and maximum retained. It is
not an area-weighted zonal climate product.
"""

from __future__ import annotations

import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path


def percentile(values: list[float], probability: float) -> float:
    """Linear percentile interpolation, matching the usual ensemble quantile."""
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def derive_model_zone_rows(
    state_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in state_rows:
        grouped[
            (
                str(row["pathway"]),
                str(row["model"]),
                str(row["variant"]),
                str(row["zone"]),
            )
        ].append(row)
    output = []
    for (pathway, model, variant, zone), rows in sorted(grouped.items()):
        temperatures = [
            float(r["temperature_anomaly_c"])
            for r in rows
            if r["temperature_anomaly_c"] is not None
        ]
        precipitation = [
            float(r["precipitation_anomaly_mm_year"])
            for r in rows
            if r["precipitation_anomaly_mm_year"] is not None
        ]
        output.append(
            {
                "pathway": pathway,
                "model": model,
                "variant": variant,
                "zone": zone,
                "state_count": len(rows),
                "temperature_anomaly_c": (
                    round(statistics.median(temperatures), 3) if temperatures else None
                ),
                "precipitation_anomaly_mm_year": (
                    round(statistics.median(precipitation), 3) if precipitation else None
                ),
            }
        )
    return output


def derive_zone_ensemble_rows(
    model_zone_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in model_zone_rows:
        grouped[(str(row["pathway"]), str(row["zone"]))].append(row)
    output = []
    for (pathway, zone), rows in sorted(grouped.items()):
        temperatures = [
            float(r["temperature_anomaly_c"])
            for r in rows
            if r["temperature_anomaly_c"] is not None
        ]
        precipitation = [
            float(r["precipitation_anomaly_mm_year"])
            for r in rows
            if r["precipitation_anomaly_mm_year"] is not None
        ]
        output.append(
            {
                "pathway": pathway,
                "zone": zone,
                "temperature_model_count": len(temperatures),
                "precipitation_model_count": len(precipitation),
                "temperature_median_c": round(statistics.median(temperatures), 2),
                "temperature_p10_c": round(percentile(temperatures, 0.10), 2),
                "temperature_p90_c": round(percentile(temperatures, 0.90), 2),
                "precipitation_median_mm_year": round(statistics.median(precipitation), 2),
                "precipitation_p10_mm_year": round(percentile(precipitation, 0.10), 2),
                "precipitation_p90_mm_year": round(percentile(precipitation, 0.90), 2),
            }
        )
    return output


def derive_zone_rows(state_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in state_rows:
        grouped[(str(row["pathway"]), str(row["zone"]))].append(row)

    output = []
    for (pathway, zone), rows in sorted(grouped.items()):
        temperatures = [float(r["temperature_anomaly_c"]) for r in rows]
        precipitation = [float(r["precipitation_anomaly_mm_year"]) for r in rows]
        output.append(
            {
                "pathway": pathway,
                "zone": zone,
                "state_count": len(rows),
                "temperature_median_c": round(statistics.median(temperatures), 2),
                "temperature_min_c": round(min(temperatures), 2),
                "temperature_max_c": round(max(temperatures), 2),
                "precipitation_median_mm_year": round(statistics.median(precipitation), 2),
                "precipitation_min_mm_year": round(min(precipitation), 2),
                "precipitation_max_mm_year": round(max(precipitation), 2),
            }
        )
    return output


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
