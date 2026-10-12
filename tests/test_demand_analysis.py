"""The four analysis reports regenerate byte for byte from config.yaml."""

from __future__ import annotations

import dataclasses

import pytest

from config_paths import ConfigError, require_path
from conftest import ROOT
from demand_analysis import (
    capture,
    carbon_intensity as ci,
    conversion_factors as cf,
    partial_adjustment as pa,
    sector_conversion as sc,
)

REPORTS = [
    ("partial_adjustment", pa.PartialAdjustmentParams, pa.report),
    ("conversion_factors", cf.ConversionFactorsParams, cf.report),
    ("sector_conversion", sc.SectorConversionParams, sc.report),
    ("carbon_intensity", ci.CarbonIntensityParams, ci.report),
]


@pytest.mark.parametrize(("section", "params_cls", "report"), REPORTS, ids=[r[0] for r in REPORTS])
def test_report_matches_committed_output(config, section, params_cls, report):
    committed = require_path(config, f"{section}.report")
    assert committed.is_relative_to(ROOT / "data")
    text = capture(report, params_cls.from_config(config))
    assert text == committed.read_text(encoding="utf-8")


def test_deviation_is_the_25th_percentile_mapping(config):
    p = pa.PartialAdjustmentParams.from_config(config)
    # (0.36 - 0.48) / 0.13: the baseline's starting elasticity against Table 5's mean.
    assert p.deviation == pytest.approx(-0.923, abs=5e-4)
    assert p.t5.long_run == pytest.approx(0.016 / 0.023)


def test_pa_path_without_income_change_stays_at_anchor(config):
    p = pa.PartialAdjustmentParams.from_config(config)
    years = p.years
    flat = {y: 9.0 for y in years}
    path = pa.pa_path(years, flat, 1.5, p.t5, g_dev0=p.deviation)
    assert all(v == pytest.approx(1.5) for v in path.values())


def test_decade_effects_require_coefficients(config):
    p = pa.PartialAdjustmentParams.from_config(config)
    with pytest.raises(ValueError, match="decade effects"):
        pa.pa_path(p.years, {y: 0.0 for y in p.years}, 0.0, p.t5, delta_mode="decade-effects")


def test_carbon_intensity_skips_africa_rows_when_not_configured(config):
    cfg = dict(config)
    cfg["inputs"] = {**config["inputs"], "iea_africa_dir": None}
    text = capture(ci.report, ci.CarbonIntensityParams.from_config(cfg))
    assert "Africa final energy not found: pass --iea-africa DIR" in text


def test_carbon_intensity_missing_africa_dir_is_an_error(config, tmp_path):
    with pytest.raises(FileNotFoundError, match="IEA Africa directory"):
        ci.CarbonIntensityParams.from_config(config, iea_africa_override=tmp_path / "absent")


def test_sector_conversion_rejects_a_stale_block_grid(config, tmp_path):
    p = sc.SectorConversionParams.from_config(config)
    text = p.baseline_block.read_text(encoding="utf-8")
    stale = tmp_path / "block.js"
    stale.write_text(text.replace("years:[2023,", "years:[2022,2023,", 2), encoding="utf-8")
    with pytest.raises(ValueError, match="year grid differs"):
        sc.block_series(dataclasses.replace(p, baseline_block=stale), "ssp245", "energyTJ")


def test_sector_conversion_rejects_an_unquoted_unsd_code(config):
    sc_cfg = config["sector_conversion"]
    carriers = {**sc_cfg["unsd"]["carriers"], 100: "coal"}  # YAML reads unquoted 0100 as 64
    cfg = {
        **config,
        "sector_conversion": {**sc_cfg, "unsd": {**sc_cfg["unsd"], "carriers": carriers}},
    }
    with pytest.raises(ConfigError, match="must be quoted"):
        sc.SectorConversionParams.from_config(cfg)
