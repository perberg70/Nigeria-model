"""Zone aggregation reproduces the committed zone CSVs offline (no network)."""

from __future__ import annotations

import csv
import dataclasses
from collections import defaultdict

import pytest

from config_paths import require_path
from conftest import read_text_lf
from regional_climate import (
    FetchSettings,
    derive_model_zone_rows,
    derive_zone_ensemble_rows,
    derive_zone_rows,
    fetch as fetch_mod,
    load_admin_units,
    write_csv,
)


@pytest.fixture(scope="module")
def settings(config):
    return FetchSettings.from_config(config)


def _read(path):
    with path.open(encoding="utf-8", newline="") as fh:
        return [{k: (None if v == "" else v) for k, v in r.items()} for r in csv.DictReader(fh)]


def _check(rows, committed, tmp_path):
    out = tmp_path / committed.name
    write_csv(out, rows)
    assert read_text_lf(out) == read_text_lf(committed)


def test_admin_units(config, settings):
    units = load_admin_units(require_path(config, "regional_climate.admin_units"))
    assert len(units) == 37
    assert len({u.zone for u in units}) == 6
    assert all(u.code.startswith(settings.iso3 + ".") for u in units)


def test_zone_summary(settings, tmp_path):
    d, n = settings.output_dir, settings.outputs
    _check(derive_zone_rows(_read(d / n["admin1"])), d / n["zone_summary"], tmp_path)


def test_model_zone_and_ensemble(settings, tmp_path):
    d, n = settings.output_dir, settings.outputs
    model_zone = derive_model_zone_rows(_read(d / n["model_admin1"]))
    _check(model_zone, d / n["model_zone"], tmp_path)
    _check(derive_zone_ensemble_rows(model_zone), d / n["zone_ensemble"], tmp_path)


def test_admin1_rows_follow_unit_file(settings):
    rows = _read(settings.output_dir / settings.outputs["admin1"])
    by_code = {u.code: u for u in settings.units}
    for r in rows:
        unit = by_code[r["code"]]
        assert (r["state"], r["zone"]) == (unit.state, unit.zone)


def test_model_zone_counts_the_states_each_median_uses():
    def row(code, t, p):
        return {
            "pathway": "ssp245",
            "model": "m",
            "variant": "r1i1p1f1",
            "code": code,
            "state": code,
            "zone": "Z",
            "temperature_anomaly_c": t,
            "precipitation_anomaly_mm_year": p,
        }

    (out,) = derive_model_zone_rows([row("a", 1.0, None), row("b", 2.0, 5.0), row("c", 3.0, None)])
    counts = [
        out[k] for k in ("state_count", "temperature_state_count", "precipitation_state_count")
    ]
    assert counts == [3, 3, 1]
    assert out["precipitation_anomaly_mm_year"] == 5.0


def test_model_run_without_data_is_flagged(settings, monkeypatch, caplog):
    monkeypatch.setattr(fetch_mod, "_get_json", lambda s, url: {"data": []})
    assert fetch_mod.fetch_model_states(settings, ("ssp245", "m", "r1i1p1f1")) == []
    assert "no data for m r1i1p1f1 ssp245" in caplog.text


def test_all_model_states_reports_dropped_runs(settings, monkeypatch, caplog):
    runs = {w: {("m", "r1i1p1f1")} for w in settings.model_pathways}
    monkeypatch.setattr(fetch_mod, "discover_model_runs", lambda s, v: defaultdict(set, runs))
    monkeypatch.setattr(fetch_mod, "_get_json", lambda s, url: {"data": None})
    assert fetch_mod.fetch_all_model_states(settings) == []
    n = len(settings.model_pathways)
    assert f"{n} of {n} model runs returned no data" in caplog.text


def test_unlisted_model_pathway_is_an_error(settings, monkeypatch):
    s = dataclasses.replace(settings, model_pathways=("ssp119",))
    monkeypatch.setattr(fetch_mod, "discover_model_runs", lambda s, v: defaultdict(set))
    with pytest.raises(ValueError, match="no individual-model runs for ssp119"):
        fetch_mod.fetch_all_model_states(s)
