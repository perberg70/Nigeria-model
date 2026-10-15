"""Zone aggregation and zone maps reproduce the committed outputs offline (no network)."""

from __future__ import annotations

import csv
import dataclasses
import json
import math
import re
from collections import defaultdict

import pytest

from config_paths import require, require_path
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
from regional_climate.zone_geometry import (
    build_zone_map,
    douglas_peucker,
    load_state_rings,
    render_js,
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


@pytest.fixture(scope="module")
def zone_inputs(config, settings):
    path = require_path(config, "regional_climate.state_boundaries")
    return path, list(settings.units), load_state_rings(path, list(settings.units))


@pytest.fixture(scope="module")
def zone_map(config, settings, zone_inputs):
    return build_zone_map(
        zone_inputs[2],
        {u.state: u.zone for u in settings.units},
        float(require(config, "regional_climate.boundary_simplify_deg")),
    )


def _rings(d):
    return [
        [tuple(map(float, pt.split())) for pt in sub.rstrip("Z").split("L")]
        for sub in d.split("M")[1:]
    ]


def _inside(point, rings):
    x, y = point
    hit = False
    for ring in rings:
        for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1], strict=True):
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                hit = not hit
    return hit


def test_zone_map_matches_prototype(config, zone_map):
    block = render_js(zone_map, str(require(config, "regional_climate.boundary_source_label")))
    html = require_path(config, "regional_climate.prototype_html").read_text(encoding="utf-8")
    assert block in html


def test_every_state_is_drawn_in_its_own_zone(settings, zone_inputs, zone_map):
    """Points inside each real state fall inside that state's drawn path and no other's."""
    rings = zone_inputs[2]
    drawn = {state: _rings(d) for state, _, d in zone_map.states}
    zone_of = {u.state: u.zone for u in settings.units}
    lons = [p[0] for rs in rings.values() for r in rs for p in r]
    lats = [p[1] for rs in rings.values() for r in rs for p in r]
    x_scale = math.cos(math.radians((min(lats) + max(lats)) / 2))
    k = 100 / ((max(lons) - min(lons)) * x_scale)
    assert {s for s, _, _ in zone_map.states} == set(zone_of)
    assert all(zone == zone_of[state] for state, zone, _ in zone_map.states)
    for state, state_rings in rings.items():
        # A grid of 0.1° points that lie inside the real state, away from its edge.
        samples = [
            (lon / 10, lat / 10)
            for lon in range(int(min(lons) * 10), int(max(lons) * 10) + 1)
            for lat in range(int(min(lats) * 10), int(max(lats) * 10) + 1)
            if _inside((lon / 10, lat / 10), state_rings)
        ]
        assert samples, state
        misplaced = 0
        for lon, lat in samples:
            point = ((lon - min(lons)) * x_scale * k, (max(lats) - lat) * k)
            owners = [s for s, r in drawn.items() if _inside(point, r)]
            misplaced += owners != [state]
        # Simplification moves borders by at most the tolerance, so only edge points may move.
        assert misplaced / len(samples) < 0.1, (state, misplaced, len(samples))


def test_unmatched_boundary_feature_is_an_error(settings, zone_inputs, tmp_path):
    path = tmp_path / "one_state.geojson"
    feature = {
        "type": "Feature",
        "properties": {"shapeISO": "XX-ZZ", "shapeName": "Nowhere"},
        "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
    }
    path.write_text(json.dumps({"features": [feature]}), encoding="utf-8")
    with pytest.raises(ValueError, match="Nowhere"):
        load_state_rings(path, list(settings.units))


def test_douglas_peucker_keeps_end_points():
    line = [(0.0, 0.0), (1.0, 0.01), (2.0, 0.0), (3.0, 2.0)]
    assert douglas_peucker(line, 0.1) == [(0.0, 0.0), (2.0, 0.0), (3.0, 2.0)]


def test_prototype_zone_names_match_zone_map(config, zone_map):
    """The hand-pasted regionalClimate zones must each have states to draw."""
    html = require_path(config, "regional_climate.prototype_html").read_text(encoding="utf-8")
    block = html[html.index("regionalClimate:{") : html.index("power:{")]
    pasted = set(re.findall(r'\{name:"([^"]+)"', block))
    assert pasted == {zone for _, zone, _ in zone_map.states}
