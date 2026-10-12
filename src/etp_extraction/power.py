"""Extract the ETP 2.0 power-sector charts from Nigeria-ETIP-u.pdf as numeric series.

The two charts on printed pages 17 (installed capacity, GW) and 18 (generation, TWh)
are VECTOR graphics: each stacked-bar segment is a filled rectangle in the PDF content
stream. Neither chart is tabulated anywhere in the document, so the values are recovered
from the rectangle geometry and calibrated against the y-axis tick labels.

Validated against figures the ETP states in prose on the same pages -- see
data/seforall_nigeria_etp/README.md.

Run: python scripts/run_etp_extraction.py --config config.yaml --chart power
Requires: pypdf
"""

from __future__ import annotations

import functools
import operator
import re
from pathlib import Path

from pypdf import PdfReader

from .document import YEARS
from .pdf_vectors import ExtractionError, colour_key, parse_page, write_csv_atomically

# Stacking order within each bar == legend reading order. Needed because the
# GENERATION chart assigns ONE colour to TWO series (Solar PV decentralized and
# Onshore wind), so colour alone is ambiguous; position in the stack resolves it.
ORDER = [
    "Coal",
    "Oil",
    "Gas On-grid",
    "Gas Captive",
    "Gas Embedded",
    "Biomass",
    "Large Hydro",
    "Solar PV",
    "Solar PV decentralized",
    "Offshore wind",
    "Onshore wind",
    "Small hydro",
    "Diesel decentralized",
    "Hydrogen",
    "Nuclear",
    "CCS (Coal, Gas, Biomass)",
    "Imports",
    "Exports",
]
CHARTS = {
    # page (1-based), bar baseline y, (y of "0" label, y of top label), value at top label,
    # x of each year column
    "generation_TWh": dict(
        page=18,
        base=94.5,
        ticks=(91.9, 395.9),
        span=600.0,
        xs=[60.0, 120.0, 180.75, 240.75, 300.75, 360.75, 420.75, 480.75, 541.5],
    ),
    "capacity_GW": dict(
        page=17,
        base=108.25,
        ticks=(105.7, 407.7),
        span=300.0,
        xs=[53.25, 113.25, 173.25, 233.25, 293.25, 353.25, 413.25, 473.25, 534.0],
    ),
}


def extract(reader, cfg):
    rects, texts = parse_page(reader.pages[cfg["page"] - 1])
    lo, hi = cfg["ticks"]
    per_pt = cfg["span"] / (hi - lo)

    # Legend: 6pt swatches paired with the nearest label to their right.
    swatches = [(c, x, y) for c, x, y, w, h in rects if 5.5 < w < 7.0 and 5.5 < h < 6.5 and y < 95]
    labels = [
        (t.strip(), x, y)
        for t, x, y in texts
        if y < 95
        and x < 560
        and t.strip() != "Overall assumptions"
        and not re.fullmatch(r"20\d\d", t.strip())
    ]
    colour_of = {}
    for t, lx, ly in labels:
        c, _, _ = min(swatches, key=lambda s: abs(s[2] - ly) * 3 + abs(s[1] - (lx - 9)))
        colour_of[t] = colour_key(c)

    bars = [r for r in rects if 23 < r[3] < 26]
    data = {}
    for year, x0 in zip(YEARS, cfg["xs"], strict=False):
        column = sorted([b for b in bars if abs(b[1] - x0) < 2], key=lambda b: b[2])
        ptr, row = 0, {}
        for c, _x, _y, _w, h in column:
            key = colour_key(c)
            while ptr < len(ORDER) and colour_of.get(ORDER[ptr]) != key:
                ptr += 1
            if ptr >= len(ORDER):
                break
            row[ORDER[ptr]] = row.get(ORDER[ptr], 0.0) + h * per_pt
            ptr += 1
        data[year] = row
    return data, h_quantum(per_pt)


def h_quantum(per_pt):
    return 0.75 * per_pt  # the geometry is quantised to 0.75pt


def csv_rows(data, unit):
    series = [k for k in ORDER if any(k in data[y] for y in YEARS)]
    yield ["series", "unit"] + [str(y) for y in YEARS]
    for s in series:
        yield [s, unit] + [f"{data[y].get(s, 0.0):.2f}" for y in YEARS]
    # Plain left-to-right addition: Python >= 3.12 sum() compensates rounding error, which
    # moves one committed TOTAL (generation 2030: 140.62 vs 140.63) across a rounding boundary.
    totals = [functools.reduce(operator.add, data[y].values(), 0.0) for y in YEARS]
    yield ["TOTAL", unit] + [f"{t:.2f}" for t in totals]


def run(pdf: Path, outdir: Path) -> None:
    reader = PdfReader(pdf)

    # Extract and VALIDATE BEFORE writing anything real. Codex found on
    # 2026-09-10 (PR #53) that the previous version wrote both real CSVs
    # unconditionally, then ran the eight prose checks below purely as PRINTED
    # diagnostics with no pass/fail gate -- so a source-deck revision or an
    # extraction regression that failed every check would still overwrite the
    # committed CSVs and exit 0. Same failure class already fixed once in the
    # companion extract_etp_demand.py; same fix here: stage to .tmp, validate,
    # promote with os.replace only if every check passes within tolerance.
    extracted = {name: extract(reader, cfg) for name, cfg in CHARTS.items()}
    gen, _ = extracted["generation_TWh"]
    cap, q_cap = extracted["capacity_GW"]
    _, q_gen = extracted["generation_TWh"]
    checks = [
        (
            "gen 2060 solar PV incl. decentralized",
            gen[2060].get("Solar PV", 0) + gen[2060].get("Solar PV decentralized", 0),
            446,
            q_gen,
        ),
        (
            "gen 2060 hydropower",
            gen[2060].get("Large Hydro", 0) + gen[2060].get("Small hydro", 0),
            39,
            q_gen,
        ),
        ("gen 2060 biomass", gen[2060].get("Biomass", 0), 32, q_gen),
        ("gen 2060 hydrogen", gen[2060].get("Hydrogen", 0), 4, q_gen),
        (
            "cap 2060 gas (on-grid+captive+embedded)",
            sum(cap[2060].get(k, 0) for k in ("Gas On-grid", "Gas Captive", "Gas Embedded")),
            11.8,
            q_cap,
        ),
        ("cap 2060 hydrogen", cap[2060].get("Hydrogen", 0), 36, q_cap),
        ("cap 2060 biomass", cap[2060].get("Biomass", 0), 6, q_cap),
        (
            "cap 2060 total excl. imports/exports",
            sum(v for k, v in cap[2060].items() if k not in ("Imports", "Exports")),
            277,
            q_cap,
        ),
    ]
    print("validation against ETP prose:")
    failures = 0
    for label, got, stated, q in checks:
        tol = max(2 * q, 1.0)
        ok = abs(got - stated) <= tol
        failures += 0 if ok else 1
        tag = "PASS" if ok else "FAIL"
        print(
            f"  {tag} {label:42} extracted {got:8.1f}   stated {stated:7}   "
            f"diff {got - stated:+6.1f}   tol +/-{tol:.1f}"
        )

    if failures:
        raise ExtractionError(f"{failures} prose check(s) FAILED — no CSV written")

    print()
    for name, _cfg in CHARTS.items():
        data, q = extracted[name]
        unit = name.split("_")[-1]
        path = outdir / f"etp_{name}.csv"
        write_csv_atomically(path, csv_rows(data, unit))
        print(f"wrote {path}  (quantum +/-{q:.2f} {unit})")
