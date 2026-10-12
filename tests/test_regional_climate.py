"""Zone aggregation reproduces the committed zone CSVs offline (no network)."""

from __future__ import annotations

import csv

import pytest

from config_paths import require_path
from conftest import read_text_lf
from regional_climate import (
    FetchSettings,
    derive_model_zone_rows,
    derive_zone_ensemble_rows,
    derive_zone_rows,
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
