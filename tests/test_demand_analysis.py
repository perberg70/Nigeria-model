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


def test_comparison_year_must_lie_inside_the_horizon(config):
    end = config["time_horizon"]["end_year"]
    cfg = {**config, "partial_adjustment": {**config["partial_adjustment"], "comparison_year": end}}
    with pytest.raises(ConfigError, match="comparison_year"):
        pa.PartialAdjustmentParams.from_config(cfg)


def test_conversion_factors_price_bases_include_the_model_row(config):
    c = config["conversion_factors"]
    bases = [u for u in c["gdp_price_bases"] if u != config["inputs"]["iiasa"]["gdp"]["unit"]]
    cfg = {**config, "conversion_factors": {**c, "gdp_price_bases": bases}}
    with pytest.raises(ConfigError, match="must be one of them"):
        cf.ConversionFactorsParams.from_config(cfg)


# --- gap flags (AGENTS.md rule 5): visible on stderr, never in the reports -----------------

UNSD_HEADER = "TIME_PERIOD,COMMODITY,TRANSACTION,OBS_VALUE,UNIT_MEASURE,CONVERSION_FACTOR\n"
IEA_HEADER = (
    "sector,coal_and_coal_products_TJ,oil_products_TJ,natural_gas_TJ,"
    "biofuels_and_waste_TJ,electricity_TJ,total_TJ\n"
)


def _warnings(caplog):
    return [r.getMessage() for r in caplog.records if r.levelname == "WARNING"]


def test_unsd_row_without_conversion_factor_in_matrix_is_an_error(config, tmp_path):
    p = sc.SectorConversionParams.from_config(config)
    f = tmp_path / "unsd.csv"
    f.write_text(UNSD_HEADER + f"{p.base_year},4670,1231,10,TN,\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no conversion factor"):
        sc.unsd_2023(dataclasses.replace(p, unsd=f))


def test_unsd_row_without_conversion_factor_elsewhere_is_left_out(config, tmp_path, caplog):
    p = sc.SectorConversionParams.from_config(config)
    f = tmp_path / "unsd.csv"
    f.write_text(
        UNSD_HEADER + f"{p.base_year},EC,133,100,MW,\n{p.base_year},4670,1231,10,TN,43.0\n",
        encoding="utf-8",
    )
    caplog.set_level("INFO")
    m, extra = sc.unsd_2023(dataclasses.replace(p, unsd=f))
    assert ("EC", "133") not in extra
    assert m["residential"]["diesel"] == pytest.approx(430.0)
    assert "1 rows without a conversion factor" in caplog.text


def _iea(p, tmp_path, rows):
    f = tmp_path / "iea.csv"
    f.write_text(IEA_HEADER + "".join(r + "\n" for r in rows), encoding="utf-8")
    zero = {s: {c: 0.0 for c in sc.CARRIERS} for s in sc.SECTORS}
    return dataclasses.replace(p, iea_final_current=f), zero


def test_iea_blank_cells_confirmed_by_row_total(config, tmp_path, caplog):
    p, u = _iea(sc.SectorConversionParams.from_config(config), tmp_path, ["Transport,,100,,,5,106"])
    caplog.set_level("INFO")
    m = sc.iea_current(p, u)
    assert m["transport"]["gas"] == 0.0
    assert "3 blank cells read as 0 TJ" in caplog.text


def test_iea_blank_cell_not_confirmed_by_row_total_is_an_error(config, tmp_path):
    p, u = _iea(sc.SectorConversionParams.from_config(config), tmp_path, ["Transport,,100,,,5,150"])
    with pytest.raises(ValueError, match="may hide a value"):
        sc.iea_current(p, u)


def test_iea_cell_without_unsd_split_is_a_flagged_proxy(config, tmp_path, caplog):
    p, u = _iea(
        sc.SectorConversionParams.from_config(config), tmp_path, ["Transport,0,100,0,0,5,105"]
    )
    m = sc.iea_current(p, u)
    assert m["transport"]["diesel"] == 100.0
    assert m["transport"]["electricity"] == 5.0
    # oil has several carriers, so assigning it all to diesel is a proxy; electricity is not
    assert _warnings(caplog) == [
        "IEA transport oil 100 TJ: UNSD has no split, so all of it is " "assigned to diesel (PROXY)"
    ]


def test_section6_missing_generation_row_prints_nan(config, monkeypatch, caplog):
    p = sc.SectorConversionParams.from_config(config)
    dropped = p.markers["ssp245"]
    real = sc.read_series

    def read_series(image_dir, filename):
        out = real(image_dir, filename)
        if filename == "Secondary Energy - Electricity - Wind.csv":
            out.pop(dropped.key)
        return out

    monkeypatch.setattr(sc, "read_series", read_series)
    text = capture(sc.section6, p)
    rows = [ln.split() for ln in text.splitlines() if ln.startswith("  ssp245") and "|" in ln]
    assert len(rows) == 3 and all(r[5] == "nan" for r in rows)
    assert any("Secondary Energy - Electricity - Wind" in w for w in _warnings(caplog))


def test_sector_conversion_flags_on_todays_data(config, caplog):
    capture(sc.report, sc.SectorConversionParams.from_config(config))
    assert _warnings(caplog) == [
        "IMAGE SSP3-7.0 lacks Primary Energy - Biomass; the values that need them are "
        "printed as nan"
    ]


def test_coverage_gaps_and_blank_parts():
    by = {
        "AAA": {2000: {"co2": 1.0, "cement_co2": 0.1}, 2001: {"co2": 1.0, "cement_co2": None}},
        "BBB": {2000: {"co2": 1.0, "cement_co2": None}, 2001: {"co2": 1.0, "cement_co2": None}},
    }
    years = [2000, 2001]
    # BBB never reports cement, so the set does not change by year; AAA's does
    assert ci.coverage_gaps(by, ["AAA", "BBB"], ["co2", "cement_co2"], years) == {
        "cement_co2": {"AAA": [2001]}
    }
    assert ci.blank_parts(by["AAA"], years, ("cement_co2",)) == {"cement_co2": [2001]}
    assert ci.year_ranges([2000, 2001, 2002, 2005, 2007, 2008]) == "2000-2002, 2005, 2007-2008"


def test_africa_final_flags_blank_biomass_years(tmp_path, caplog):
    files = ci.AggregateFiles(
        total_by_sector="total.csv",
        by_source="{sector}_by_source.csv",
        sectors=("residential", "commercial", "industry", "transport"),
    )

    def write(name, rows):
        body = "".join(f"{label},{v},{y}, TJ\n" for label, v, y in rows)
        (tmp_path / name).write_text("label,value,year,unit\n" + body, encoding="utf-8")

    write("total.csv", [("Total", 100, 2000)] * 1)
    for s in ("residential", "commercial", "industry"):
        write(f"{s}_by_source.csv", [("Biofuels and waste", 10, 2000)])
    write("transport_by_source.csv", [("Biofuels and waste", "", 2000)])
    tfc, com = ci.africa_final(tmp_path, files)
    assert com[2000] == pytest.approx(70.0)
    assert _warnings(caplog) == [
        "IEA Africa transport biofuels and waste blank in 2000; commercial final energy "
        "counts it as 0 there"
    ]


def test_carbon_intensity_flags_on_todays_data(config, caplog):
    capture(ci.report, ci.CarbonIntensityParams.from_config(config))
    heads = sorted(w.split(":")[0] for w in _warnings(caplog))
    assert heads == [
        "IEA Africa transport biofuels and waste blank in 2000-2007; commercial final energy "
        "counts it as 0 there",
        "OWID cement_co2",
        "OWID coal_co2",
        "OWID gas_co2",
    ]
