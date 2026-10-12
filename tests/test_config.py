"""The configuration contract: explicit --config, named gaps, traceable values."""

from __future__ import annotations

import csv
import subprocess
import sys

import pytest

from config_paths import ConfigError, load_config, require, require_path, resolve_path
from conftest import ROOT

SCRIPTS = sorted(p.name for p in (ROOT / "scripts").glob("*.py") if not p.name.startswith("_"))


def test_every_script_is_listed():
    assert "__init__.py" not in SCRIPTS
    assert len(SCRIPTS) == 7


@pytest.mark.parametrize("script", SCRIPTS)
def test_script_requires_config(script):
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script)],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert proc.returncode == 2
    assert "--config" in proc.stderr


def test_require_names_the_missing_key(config):
    with pytest.raises(ConfigError, match="'ssp_baseline.anchors.nope'"):
        require(config, "ssp_baseline.anchors.nope")


def test_paths_resolve_against_config_directory(config, tmp_path):
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text("a: {b: data/x.csv}\n", encoding="utf-8")
    cfg = load_config(cfg_file)
    assert require_path(cfg, "a.b") == tmp_path / "data" / "x.csv"
    assert resolve_path(config, "config.yaml") == ROOT / "config.yaml"


def test_every_configured_input_exists(config):
    for key in (
        "inputs.image_dir",
        "inputs.iiasa.csv",
        "inputs.unsd_energy",
        "inputs.owid_co2",
        "inputs.wdi_gdp_growth",
        "inputs.etp_cooking",
        "etp_extraction.pdf",
        "regional_climate.admin_units",
    ):
        assert require_path(config, key).exists(), key
    for key in require(config, "inputs.iea"):
        assert require_path(config, f"inputs.iea.{key}").exists(), key


def test_scenario_names_are_qualified_by_model(config):
    for pathway, entry in require(config, "scenarios").items():
        assert entry["model"] and entry["scenario"], pathway


def test_coal_factor_matches_ipcc_table(config):
    path = require_path(config, "inputs.ipcc_emission_factors")
    with path.open(encoding="utf-8-sig") as fh:
        rows = {r[0]: r for r in csv.reader(fh)}
    kg_per_tj = float(rows["Other Bituminous Coal"][2])
    assert require(config, "carbon_intensity.coal_emission_factor") == kg_per_tj / 1000
