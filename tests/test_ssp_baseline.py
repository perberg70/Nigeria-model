"""The baseline block and the prototype splice regenerate from config.yaml."""

from __future__ import annotations

import dataclasses
import logging

import pytest

from ssp_baseline import (
    BaselineParams,
    block_series,
    build_baseline,
    check_iea_anchors,
    render_block,
    update_prototype_html,
)


@pytest.fixture(scope="module")
def params(config):
    return BaselineParams.from_config(config)


@pytest.fixture(scope="module")
def block_text(params):
    return render_block(build_baseline(params))


def test_block_matches_committed_file(params, block_text):
    assert block_text == params.output_block.read_text(encoding="utf-8")


def test_prototype_splice_is_idempotent_on_committed_html(params, block_text):
    html = params.prototype_html.read_text(encoding="utf-8")
    assert update_prototype_html(html, block_text) == html


def test_splice_replaces_a_stale_block(params, block_text):
    html = params.prototype_html.read_text(encoding="utf-8")
    stale = html.replace(
        "pollutingIdxSSP:{\n      eps:-0.67", "pollutingIdxSSP:{\n      eps:-0.99", 1
    )
    assert stale != html
    assert update_prototype_html(stale, block_text) == html


def test_anchor_year_emissions_reproduced(params, block_text):
    years = params.years
    result = build_baseline(params)
    for rec in result.block.values():
        assert rec["emisMt"][years.index(params.anchor_year)] == pytest.approx(
            params.anchor_mt, abs=1e-3
        )
    energy = block_series(block_text, "ssp245", "energyTJ")
    assert energy[0] == pytest.approx(params.tfe_tj, rel=1e-9)


def test_markers_carry_model_and_scenario(params):
    for marker in params.markers.values():
        assert marker.key == (marker.model, marker.scenario)


def test_anchor_drift_from_iea_table_is_an_error(params):
    drifted = dataclasses.replace(params, grid_gwh=params.grid_gwh + 1.0)
    with pytest.raises(ValueError, match="grid total"):
        check_iea_anchors(drifted)


def test_missing_iea_tables_are_flagged_not_silent(params, tmp_path, caplog):
    missing = dataclasses.replace(params, iea_final_current=tmp_path / "absent.csv")
    with caplog.at_level(logging.WARNING):
        check_iea_anchors(missing)
    assert "not cross-checked" in caplog.text
