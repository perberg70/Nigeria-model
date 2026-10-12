"""The ETP chart extraction reproduces the committed CSVs from the PDF."""

from __future__ import annotations

import csv
import io
import types

import pytest

from config_paths import require_path
from conftest import read_text_lf

pytest.importorskip("pypdf")

from etp_extraction import CHARTS, ExtractionError, power  # noqa: E402

# Reproduced exactly (after CRLF -> LF) by a fresh extraction.
EXACT = ["etp_capacity_GW.csv", "etp_cooking.csv", "etp_industry_PJ.csv"]
# Reproduced to within 0.01 of a printed value: the committed etp_generation_TWh.csv has 2030
# TOTAL 140.63 against 140.62 now, a rounding-boundary difference far inside the chart's
# +/-1.48 TWh drawing quantum (see data/seforall_nigeria_etp/README.md).
CLOSE = ["etp_generation_TWh.csv", "etp_oil_BAU_demand_PJ.csv", "etp_gas_BAU_demand_PJ.csv"]


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


@pytest.mark.parametrize("name", CLOSE)
def test_close_reproduction(extracted, name):
    out, committed = extracted
    new = list(csv.reader(io.StringIO(read_text_lf(out / name))))
    old = list(csv.reader(io.StringIO(read_text_lf(committed / name))))
    assert [r[:2] for r in new] == [r[:2] for r in old]
    assert new[0] == old[0]
    for a, b in zip(new[1:], old[1:], strict=True):
        for x, y in zip(a[2:], b[2:], strict=True):
            assert float(x) == pytest.approx(float(y), abs=0.0101)


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
