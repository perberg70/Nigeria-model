"""The ETP chart extraction reproduces the committed CSVs from the PDF."""

from __future__ import annotations

import pytest

from config_paths import require_path
from conftest import read_text_lf

pytest.importorskip("pypdf")

from etp_extraction import CHARTS  # noqa: E402

# Every committed CSV is reproduced exactly once CRLF is normalised to LF (the extractors write
# CRLF; the oil/gas demand CSVs are stored with LF).
EXACT = [
    "etp_capacity_GW.csv",
    "etp_generation_TWh.csv",
    "etp_oil_BAU_demand_PJ.csv",
    "etp_gas_BAU_demand_PJ.csv",
    "etp_cooking.csv",
    "etp_industry_PJ.csv",
]


@pytest.fixture(scope="module")
def extracted(config, tmp_path_factory):
    out = tmp_path_factory.mktemp("etp")
    pdf = require_path(config, "etp_extraction.pdf")
    for module in CHARTS.values():
        module.run(pdf, out)
    return out, require_path(config, "etp_extraction.output_dir")


@pytest.mark.parametrize("name", EXACT)
def test_exact_reproduction(extracted, name):
    out, committed = extracted
    assert read_text_lf(out / name) == read_text_lf(committed / name)


def test_no_staging_files_left(extracted):
    out, _ = extracted
    assert not list(out.glob("*.tmp"))
