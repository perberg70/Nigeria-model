"""Shared readers: (model, scenario) identity, interpolation, IIASA validation."""

from __future__ import annotations

import pytest

from config_paths import require_path
from scenario_data import IiasaExport, country_series, interp, load_markers, read_series


def test_image_series_keyed_by_model_and_scenario(config):
    series = read_series(require_path(config, "inputs.image_dir"), "Final Energy.csv")
    markers = load_markers(config)
    assert all(isinstance(k, tuple) and len(k) == 2 for k in series)
    for marker in markers.values():
        assert marker.key in series


def test_same_scenario_name_under_two_models_stays_apart(tmp_path):
    (tmp_path / "x.csv").write_text(
        "Run ID,Scenario name,Model name,Variable name,unit,Flag Category,year,value\n"
        "1,S1,MODEL A,X,EJ/yr,,2020,1.0\n"
        "2,S1,MODEL B,X,EJ/yr,,2020,2.0\n",
        encoding="utf-8",
    )
    series = read_series(tmp_path, "x.csv")
    assert series[("MODEL A", "S1")] == {2020: 1.0}
    assert series[("MODEL B", "S1")] == {2020: 2.0}


def test_interp():
    d = {2020: 1.0, 2030: 3.0}
    assert interp(2010, d) == 1.0
    assert interp(2040, d) == 3.0
    assert interp(2025, d) == pytest.approx(2.0)


def test_country_series_fills_base_years(config):
    iiasa = IiasaExport.from_config(config)
    pop = iiasa.series(iiasa.population, ["SSP2"], (2023, 2024))
    assert {2023, 2024} <= set(pop["SSP2"])
    assert pop["SSP2"][2023] == pytest.approx(
        interp(2023, {2020: pop["SSP2"][2020], 2025: pop["SSP2"][2025]})
    )


def test_country_series_missing_narrative_is_an_error(config):
    iiasa = IiasaExport.from_config(config)
    with pytest.raises(ValueError, match="missing narrative rows: SSP9"):
        country_series(
            iiasa.path,
            iiasa.population.variable,
            ["SSP2", "SSP9"],
            unit=iiasa.population.unit,
            history_end=iiasa.history_end,
            fill_years=(2023, 2024),
        )
