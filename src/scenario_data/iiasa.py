"""Read the IIASA SSP Scenario Explorer export (population, GDP|PPP) for one country."""

from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config_paths import require, require_path

from .image import interp

HISTORICAL = "Historical Reference"


@dataclass(frozen=True)
class SeriesSpec:
    """One variable of the export: its name, unit and the scale to absolute units."""

    model: str
    variable: str
    unit: str
    scale: float


@dataclass(frozen=True)
class IiasaExport:
    """The configured IIASA export (``inputs.iiasa``)."""

    path: Path
    history_end: int
    region: str
    population: SeriesSpec
    gdp: SeriesSpec

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> IiasaExport:
        def spec(name: str) -> SeriesSpec:
            base = f"inputs.iiasa.{name}"
            return SeriesSpec(
                model=require(config, f"{base}.model"),
                variable=require(config, f"{base}.variable"),
                unit=require(config, f"{base}.unit"),
                scale=float(require(config, f"{base}.scale")),
            )

        return cls(
            path=require_path(config, "inputs.iiasa.csv"),
            history_end=int(require(config, "inputs.iiasa.history_end_year")),
            region=require(config, "inputs.iiasa.region"),
            population=spec("population"),
            gdp=spec("gdp"),
        )

    def series(
        self, spec: SeriesSpec, narratives: Iterable[str], fill_years: Iterable[int]
    ) -> dict[str, dict[int, float]]:
        return country_series(
            self.path,
            spec.variable,
            narratives,
            model=spec.model,
            region=self.region,
            unit=spec.unit,
            scale=spec.scale,
            history_end=self.history_end,
            fill_years=fill_years,
        )


def _year_columns(row: dict[str, str], scale: float) -> dict[int, float]:
    return {
        int(k): float(v) * scale
        for k, v in row.items()
        if k.strip().isdigit() and v not in ("", None)
    }


def country_series(
    path: Path,
    variable: str,
    narratives: Iterable[str],
    *,
    model: str,
    region: str,
    unit: str | None = None,
    scale: float = 1.0,
    history_end: int,
    fill_years: Iterable[int],
) -> dict[str, dict[int, float]]:
    """The country's own population or GDP to 2100 -- no regional transfer.

    The export carries one Historical Reference row through ``history_end`` and
    separate narrative rows from ``history_end`` onward. Historical values are
    shared by all narratives; each of ``fill_years`` missing from the grid (the
    base and anchor years, on this five-yearly export) is linearly interpolated
    between the historical anchors. Scenario rows supply ``history_end`` onward.
    Rows are matched on ``(model, scenario)`` within ``region``; a repeated row raises.
    """

    wanted = set(narratives)
    historical = None
    forecasts = {}
    with path.open(encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if r["variable"] != variable or r["model"] != model or r["region"] != region:
                continue
            if unit is not None and r["unit"] != unit:
                continue
            yrs = _year_columns(r, scale)
            if r["scenario"] == HISTORICAL:
                if historical is not None:
                    raise ValueError("%s: repeated Historical Reference row" % variable)
                historical = yrs
            elif r["scenario"] in wanted:
                if r["scenario"] in forecasts:
                    raise ValueError("%s: repeated %s row" % (variable, r["scenario"]))
                forecasts[r["scenario"]] = yrs

    fill = list(fill_years)
    if historical is None:
        raise ValueError("%s: Historical Reference row is missing" % variable)
    if history_end not in historical or not any(y <= min(fill) for y in historical):
        raise ValueError(
            "%s: Historical Reference must bracket %s and contain %d"
            % (variable, fill, history_end)
        )

    out = {}
    for narrative, forecast in forecasts.items():
        yrs = {y: v for y, v in historical.items() if y <= history_end}
        yrs.update(forecast)
        for y in fill:
            if y not in yrs:
                yrs[y] = interp(y, historical)
        out[narrative] = yrs

    missing = sorted(wanted - set(out))
    if missing:
        raise ValueError("%s: missing narrative rows: %s" % (variable, ", ".join(missing)))
    return out


def historical_series(
    path: Path, variable: str, unit: str, *, model: str, region: str
) -> dict[int, float]:
    """The Historical Reference row of one variable of one model and region, unscaled."""

    found = []
    with path.open(encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if (
                r["scenario"] == HISTORICAL
                and r["model"] == model
                and r["region"] == region
                and r["variable"] == variable
                and r["unit"] == unit
            ):
                found.append(_year_columns(r, 1.0))
    if len(found) != 1:
        raise ValueError(
            f"{path.name}: {len(found)} Historical Reference rows for {model} {variable} [{unit}]"
        )
    return found[0]
