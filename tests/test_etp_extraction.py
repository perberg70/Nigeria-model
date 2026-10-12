"""The ETP chart extraction reproduces the committed CSVs from the PDF."""

from __future__ import annotations

import types

import pytest

from config_paths import require_path
from conftest import read_text_lf

pytest.importorskip("pypdf")

from etp_extraction import CHARTS, ExtractionError, power  # noqa: E402

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


# Synthetic page: two legend entries and one bar column, to exercise the stack-order gate.
RED, BLUE, GREEN = (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0, 0.0)
SYNTH = dict(page=1, base=0.0, ticks=(0.0, 100.0), span=100.0, xs=[50.0])


def _extract(monkeypatch, bars):
    legend = [(RED, 100.0, 50.0, 6.0, 6.0), (BLUE, 200.0, 50.0, 6.0, 6.0)]
    texts = [("Coal", 109.0, 50.0), ("Oil", 209.0, 50.0)]
    monkeypatch.setattr(power, "parse_page", lambda page: (legend + bars, texts))
    return power.extract(types.SimpleNamespace(pages=[None]), SYNTH)


def _bar(colour, y, h, x=50.0):
    return (colour, x, y, 24.0, h)


def test_power_stack_in_order(monkeypatch):
    data, _ = _extract(monkeypatch, [_bar(RED, 0.0, 10.0), _bar(BLUE, 10.0, 5.0)])
    assert data[2020] == {"Coal": 10.0, "Oil": 5.0}


@pytest.mark.parametrize("colour", [RED, GREEN], ids=["out-of-order", "unknown"])
def test_power_segment_off_the_stack_order_is_an_error(monkeypatch, colour):
    with pytest.raises(ExtractionError, match="does not follow the stack order after Oil"):
        _extract(monkeypatch, [_bar(BLUE, 0.0, 10.0), _bar(colour, 10.0, 5.0)])


def test_power_bar_outside_year_columns_is_an_error(monkeypatch):
    with pytest.raises(ExtractionError, match="match no year column"):
        _extract(monkeypatch, [_bar(RED, 0.0, 10.0), _bar(BLUE, 0.0, 5.0, x=80.0)])
