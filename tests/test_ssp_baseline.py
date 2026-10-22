"""The baseline block and the prototype splice regenerate from config.yaml."""

from __future__ import annotations

import dataclasses
import math

import pytest

from config_paths import ConfigError
from scenario_data import interp, read_series
from ssp_baseline import (
    BaselineParams,
    block_series,
    build_baseline,
    check_iea_anchors,
    render_block,
    update_prototype_html,
    write_prototype,
)
from ssp_baseline.builder import log_income_ratio


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


def test_electrification_starts_at_the_anchor(params, block_text):
    for pid in params.markers:
        share = block_series(block_text, pid, "elecShare")
        assert share[params.years.index(params.base_year)] == pytest.approx(
            params.elec_base, abs=1e-6
        )


@pytest.mark.parametrize("log_income", [-0.3, 0.5, 2.5])
def test_share_law_times_final_energy_law_is_the_electricity_law(params, log_income):
    # Electricity = share x final energy, so the income effect is counted once.
    L = log_income
    final_energy = math.exp(params.elasticity * L + params.elasticity_q * L * L)
    electricity = math.exp(params.elec_elasticity * L + params.elec_elasticity_q * L * L)
    assert params.share_income_factor(L) * final_energy == pytest.approx(electricity)


def test_block_electricity_is_the_electricity_law_times_r10_residual(params, block_text):
    # Nigeria's electricity index (share x final energy, from the block) equals its
    # population and the electricity law times R10's electricity path over R10's population
    # and the same law, both R10 residuals together, rebuilt from the raw series.
    years, b = params.years, params.base_year
    result = build_baseline(params)
    r10_elec = read_series(params.image_dir, "Secondary Energy - Electricity.csv")
    r10_gdp = read_series(params.image_dir, "GDP - PPP.csv")
    r10_pop = read_series(params.image_dir, "Population.csv")

    def law(L):
        return math.exp(params.elec_elasticity * L + params.elec_elasticity_q * L * L)

    for pid, marker in params.markers.items():
        share = block_series(block_text, pid, "elecShare")
        energy = block_series(block_text, pid, "energyTJ")
        gdp, pop = result.gdp[marker.narrative], result.pop[marker.narrative]
        rg, rp, re = r10_gdp[marker.key], r10_pop[marker.key], r10_elec[marker.key]
        for y in (2030, 2050, 2077, 2100):
            i, i0 = years.index(y), years.index(b)
            got = share[i] * energy[i] / (share[i0] * energy[i0])
            nga = interp(y, pop) / interp(b, pop) * law(log_income_ratio(y, b, gdp, pop))
            r10 = (interp(y, re) / interp(b, re)) / (
                interp(y, rp) / interp(b, rp) * law(log_income_ratio(y, b, rg, rp))
            )
            assert got == pytest.approx(nga * r10, rel=1e-4)


def test_income_span_is_the_papers_25th_to_75th_percentile(params):
    assert params.income_span_log == pytest.approx(2.0)


@pytest.mark.parametrize("key", ["electricity_elasticity", "electricity_elasticity_quadratic"])
def test_electricity_law_is_required(config, key):
    demand = {k: v for k, v in config["ssp_baseline"]["demand"].items() if k != key}
    cfg = {**config, "ssp_baseline": {**config["ssp_baseline"], "demand": demand}}
    with pytest.raises(ConfigError, match=key):
        BaselineParams.from_config(cfg)


def test_share_law_past_the_papers_range_is_logged(params, caplog):
    caplog.set_level("WARNING", logger="ssp_baseline.builder")
    result = build_baseline(params)
    warned = [r.getMessage() for r in caplog.records if r.levelname == "WARNING"]
    assert warned
    for pid, rec in result.block.items():
        for who, key in (("R10", "r10IncomeLog"), (params.region_name, "incomeLog")):
            past = max(rec[key]) >= params.income_span_log
            assert past == any(m.startswith(f"{pid}: {who} ") for m in warned)


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
