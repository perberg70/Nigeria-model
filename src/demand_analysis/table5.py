"""Burke & Csereklyei (2016) coefficients and the baseline's current demand law."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from typing import Any

from config_paths import require

TABLE5 = "parameters.burke_csereklyei_2016.table5"


@dataclass(frozen=True)
class Table5Column:
    """One column of Table 5 (10-year growth-rates model)."""

    beta: float  # 10-year elasticity at mean initial log income
    eta: float  # interaction per log unit of (demeaned) initial income
    theta: float  # initial log income level
    kappa: float  # initial log energy level (conditional convergence)
    b25: float
    b75: float
    lr: float

    @property
    def lam(self) -> float:
        """Annual closing speed, linearisation: -kappa."""
        return -self.kappa

    @property
    def long_run(self) -> float:
        """-theta/kappa, the long-run-implied elasticity."""
        return -self.theta / self.kappa


@dataclass(frozen=True)
class CurrentLaw:
    """The baseline's integrated 10-year law, ln(E/E0) = b L + q L^2 (ssp_baseline.demand)."""

    elasticity: float
    quadratic: float


def load_table5(config: Mapping[str, Any]) -> dict[str, Table5Column]:
    columns = require(config, TABLE5)
    return {
        name: Table5Column(
            **{f.name: require(config, f"{TABLE5}.{name}.{f.name}") for f in fields(Table5Column)}
        )
        for name in columns
    }


def load_current_law(config: Mapping[str, Any]) -> CurrentLaw:
    return CurrentLaw(
        elasticity=require(config, "ssp_baseline.demand.elasticity"),
        quadratic=require(config, "ssp_baseline.demand.elasticity_quadratic"),
    )
