"""Scenario markers: prototype pathway ids mapped to (model, scenario) and an SSP narrative."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from config_paths import ConfigError, require

from .image import ScenarioKey


@dataclass(frozen=True)
class Marker:
    """One prototype pathway: its IAM scenario and the SSP narrative of its population path."""

    pathway: str
    label: str
    model: str
    scenario: str
    narrative: str

    @property
    def key(self) -> ScenarioKey:
        return (self.model, self.scenario)


def load_markers(config: Mapping[str, Any]) -> dict[str, Marker]:
    """``scenarios`` section of the config, in file order."""

    section = require(config, "scenarios")
    if not isinstance(section, Mapping) or not section:
        raise ConfigError("config key 'scenarios' must be a non-empty mapping")
    markers = {}
    for pathway in section:
        base = f"scenarios.{pathway}"
        markers[pathway] = Marker(
            pathway=pathway,
            label=require(config, f"{base}.label"),
            model=require(config, f"{base}.model"),
            scenario=require(config, f"{base}.scenario"),
            narrative=require(config, f"{base}.narrative"),
        )
    return markers


def narratives(markers: Mapping[str, Marker]) -> list[str]:
    """Distinct SSP narratives, in marker order."""

    out: list[str] = []
    for marker in markers.values():
        if marker.narrative not in out:
            out.append(marker.narrative)
    return out
