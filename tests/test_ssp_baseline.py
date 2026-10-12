"""The baseline block and the prototype splice regenerate from config.yaml."""

from __future__ import annotations

import dataclasses

import pytest

from config_paths import ConfigError
from ssp_baseline import (
    BaselineParams,
    block_series,
    build_baseline,
    check_iea_anchors,
    render_block,
    update_prototype_html,
    write_prototype,
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


@pytest.mark.parametrize(
    "anchor", ["emissions:{", "sspBaseline:{", "popSSP:{", "pollutingIdxSSP:{"]
)
def test_splice_replaces_a_stale_block(params, block_text, anchor):
    html = params.prototype_html.read_text(encoding="utf-8")
    assert html.count(anchor) == 1
    stale = html.replace(anchor, anchor + "\n           staleKey:1,", 1)
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
    generation = {**params.generation_gwh, "Gas": params.generation_gwh["Gas"] + 1.0}
    drifted = dataclasses.replace(params, generation_gwh=generation)
    with pytest.raises(ValueError, match="Gas generation differs from the saved IEA table"):
        check_iea_anchors(drifted)


def test_source_without_iea_line_must_be_an_observed_zero(params):
    assert "Wind" not in params.iea_generation_lines
    generation = {**params.generation_gwh, "Wind": 1.0}
    with pytest.raises(ValueError, match="Wind generation differs"):
        check_iea_anchors(dataclasses.replace(params, generation_gwh=generation))


def test_generation_must_list_every_source(config):
    anchors = {**config["ssp_baseline"]["anchors"]}
    anchors["generation_gwh"] = {
        k: v for k, v in anchors["generation_gwh"].items() if k != "Nuclear"
    }
    cfg = {**config, "ssp_baseline": {**config["ssp_baseline"], "anchors": anchors}}
    with pytest.raises(ConfigError, match="generation_gwh must list every source"):
        BaselineParams.from_config(cfg)


def test_grid_anchor_is_the_sum_of_the_iea_lines(params):
    assert params.grid_gwh == 40975.0
    assert params.lowmix_base["Wind"] == 0.0


def test_missing_iea_table_is_an_error(params, tmp_path):
    missing = dataclasses.replace(params, iea_final_current=tmp_path / "absent.csv")
    with pytest.raises(FileNotFoundError, match="anchors unchecked"):
        check_iea_anchors(missing)


def test_write_prototype_reproduces_committed_html(params, block_text, tmp_path):
    target = tmp_path / "africa-prototype.html"
    target.write_bytes(params.prototype_html.read_bytes())
    write_prototype(target, block_text)
    assert target.read_bytes() == params.prototype_html.read_bytes()
    assert not list(tmp_path.glob("*.tmp"))


def test_failed_splice_leaves_prototype_untouched(params, block_text, tmp_path):
    html = params.prototype_html.read_bytes()
    anchor = b"  /* --- Social Cost of Carbon"
    assert html.count(anchor) == 1
    broken = html.replace(anchor, b"  /* --- SCC", 1)
    target = tmp_path / "africa-prototype.html"
    target.write_bytes(broken)
    with pytest.raises(ValueError):
        write_prototype(target, block_text)
    assert target.read_bytes() == broken
    assert not list(tmp_path.glob("*.tmp"))
