#!/usr/bin/env python3
"""Extract the ETP 2.0 oil- and gas-demand-by-sector charts (printed page 22) as series.

Companion to `extract_etp_charts.py`, which does the power-sector charts on pages 17-18.
Page 22 carries FOUR small stacked-bar charts -- oil and gas demand by consuming sector,
each under a BAU and an NZE scenario, all in PJ. Like the power charts they are vector
graphics with no underlying table published anywhere in the document.

The oil/BAU chart is the one that matters for the genset boundary question: its `Power`
segment is the ETP's own assumption for oil burned to generate electricity, which is the
fuel behind the `Diesel decentralized` row of the generation chart on page 18.

Calibration is checked against the one figure the ETP states in prose for these charts:
"the oil demand is almost halved by 2060 in comparison to 2020 (550 PJ in 2060)" (p.22).

Usage:  python3 extract_etp_demand.py <path-to-Nigeria-ETIP-u.pdf> [outdir]
Requires: pypdf, and extract_etp_charts.py alongside this file.
"""
import csv, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_etp_charts import parse_page                      # noqa: E402
from pypdf import PdfReader                                    # noqa: E402

# Series are identified by COLOUR, not by position in the stack. Position fails here:
# several series are zero in several years, so a segment's index in the sorted stack does
# not identify it. Unlike the generation chart on p.18 (where two series share one RGB),
# every series on p.22 has a distinct colour, so colour is exact.
#
# The map is read from the legend itself -- the six swatches are 4.5 pt filled squares at
# x~606, each paired with its label at x~613 on the same line -- so it is derived from the
# document rather than assumed. `legend_map()` below re-derives it on every run.
ORDER = ['Power', 'Hydrogen', 'Industry', 'Transport', 'Residential', 'Commercial']
YEARS = [2020, 2025, 2030, 2035, 2040, 2045, 2050, 2055, 2060]

# Each chart: the x/y window that isolates it on the page, the y band holding its year
# labels, the y of the "0" and top tick LABELS, and the value at the top label.
#
# Year columns are NOT hard-coded. They are located per chart by matching the bars to the
# nine year labels printed under that chart (see `columns()`), because the four charts do
# not share an x grid and a year with no bars at all would silently shift a positional
# assignment. An earlier version of this file did hard-code them, guessed the NZE offset,
# and produced NZE CSVs that were almost entirely zeros -- caught in Codex review of PR #53
# on 2026-08-30 and fixed here.
#
# NOTE on `base`: the axis line sits ~3 pt above the "0" label's text baseline, the same
# offset `extract_etp_charts.py` carries for the power charts. It is taken here from the
# bottom edge of the lowest filled segment, which is exact.
CHARTS = {
    'oil_BAU': dict(win=(70, 305, 283, 405), labely=(255, 268),
                    base=290.25, ticks=(287.1, 401.0), span=1000.0),
    'gas_BAU': dict(win=(70, 305, 50, 175), labely=(21, 34),
                    base=57.0, ticks=(52.9, 166.8), span=3000.0),
}

# ⚠️ THE TWO NZE CHARTS ARE NOT EXTRACTED, DELIBERATELY.
#
# Their geometry is readable, but the year assignment is not resolvable by the method used
# above. The bar-to-label offset on this page is about 10.7 pt while the column spacing is
# about 21.5 pt -- almost exactly half -- so every bar sits nearly equidistant between two
# year labels and "nearest label" can shift the whole series by one column. The two BAU
# charts happen to resolve consistently and are confirmed by their prose checks; the NZE
# charts do not.
#
# The tell: with the offset fitted one way, gas NZE 2035 extracts as 296 PJ against the
# ETP's own stated "650 PJ in 2035" (p.22). That is a failed check, not a rounding
# difference, so no NZE CSV is written and none is committed.
#
# History: an earlier version of this file hard-coded guessed NZE x positions and wrote
# CSVs that were almost entirely zeros. Caught in Codex review of PR #53 on 2026-08-30.
# Resolving this properly needs an anchor independent of the year labels -- the plot area's
# own left edge, or the axis rule -- which was not attempted.
#
# [GAP: ETP oil and gas demand under the NZE scenario is not extracted. Only BAU is
# available from this folder. Nothing in 03_models/ currently depends on the NZE series.]
NZE_UNRESOLVED = {
    'oil_NZE': dict(win=(380, 615, 283, 405), labely=(255, 268),
                    base=290.25, ticks=(287.1, 401.0), span=1000.0),
    'gas_NZE': dict(win=(380, 615, 50, 175), labely=(21, 34),
                    base=57.0, ticks=(52.9, 166.8), span=3000.0),
}

# Figures the ETP states in prose on p.22, used to validate the extraction. The run fails
# loudly rather than writing a CSV that does not reproduce the document's own numbers.
PROSE_CHECKS = {
    'oil_BAU': (2060, 550.0, '"the oil demand is almost halved by 2060 ... (550 PJ in 2060)"'),
    'gas_BAU': (2060, 2740.0, '"natural gas demand increases by more than 8 times (2,740 PJ in 2060)"'),
}

PAGE = 22           # 1-based printed page, which is also the PDF page index here
QUANTUM_PT = 0.75   # the geometry quantum: no segment edge is finer than this


def legend_map(rects, texts):
    """Derive {rgb: series_name} from the legend swatches printed on the page."""
    labels = [(t.strip(), x, y) for t, x, y in texts if t.strip() in ORDER]
    swatches = [r for r in rects if 2 < r[3] < 9 and 2 < r[4] < 9]
    out = {}
    for name, lx, ly in labels:
        near = [s for s in swatches if 0 < lx - s[1] < 20 and abs(s[2] - ly) < 6]
        if near:
            rgb = tuple(round(c, 3) for c in near[0][0])
            if rgb in out and out[rgb] != name:
                raise SystemExit(f'legend colour clash: {rgb} -> {out[rgb]} and {name}')
            out[rgb] = name
    missing = set(ORDER) - set(out.values())
    if missing:
        raise SystemExit(f'legend swatches not found for: {sorted(missing)}')
    return out


def columns(rects, texts, cfg):
    """Locate the nine year columns of one chart, from its printed year labels.

    The bars sit at a constant offset from their labels; the offset is fitted from the
    bars actually present rather than assumed, so a year with no bars costs nothing.
    Returns the list of nine bar-centre x positions, in YEARS order.
    """
    x0, x1, ylo, yhi = cfg['win']
    ly0, ly1 = cfg['labely']
    labels = sorted(x for t, x, y in texts
                    if t.strip().isdigit() and len(t.strip()) == 4
                    and x0 < x < x1 and ly0 < y < ly1)
    if len(labels) != len(YEARS):
        raise SystemExit(f'expected {len(YEARS)} year labels, found {len(labels)}')

    bars = sorted({round(r[1], 2) for r in rects
                   if x0 < r[1] < x1 and ylo < r[2] < yhi and 10 < r[3] < 25 and r[4] > 0.3})
    if not bars:
        raise SystemExit('no bars found in window')
    offsets = [min((b - l for l in labels), key=abs) for b in bars]
    offsets.sort()
    offset = offsets[len(offsets) // 2]                # median, robust to a stray fill
    return [l + offset for l in labels]


def series(rects, texts, cfg, cmap):
    """Resolve the segments of one chart into {series_name: [value per year]}."""
    y0, y1 = cfg['ticks']
    scale = cfg['span'] / (y1 - y0)                    # PJ per point
    x0, x1, ylo, yhi = cfg['win']
    out = {name: [0.0] * len(YEARS) for name in ORDER}

    for col, xc in enumerate(columns(rects, texts, cfg)):
        segs = [r for r in rects
                if abs(r[1] - xc) < 6 and x0 < r[1] < x1 and ylo < r[2] < yhi
                and r[3] < 25 and r[4] > 0.3]
        for rgb, _x, _y, _w, h in segs:
            name = cmap.get(tuple(round(c, 3) for c in rgb))
            if name:                                   # ignore gridlines / stray fills
                out[name][col] += round(h * scale, 1)
    return out, scale


def main(pdf, outdir='.'):
    rects, texts = parse_page(PdfReader(pdf).pages[PAGE - 1])
    cmap = legend_map(rects, texts)
    failures = 0
    # Write to .tmp and promote only after EVERY prose check has passed. Codex found on
    # 2026-09-08 (PR #53) that the previous version opened the real path with 'w' before the
    # checks ran, so a failed run exited nonzero but left an invalid CSV on disk -- contrary
    # to what this folder's README and the review log both claimed.
    pending = []
    for name, cfg in CHARTS.items():
        data, scale = series(rects, texts, cfg, cmap)
        totals = [sum(data[s][i] for s in ORDER) for i in range(len(YEARS))]
        path = os.path.join(outdir, f'etp_{name}_demand_PJ.csv')
        tmp = path + '.tmp'
        with open(tmp, 'w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh)
            w.writerow(['series', 'unit'] + YEARS)
            for s in ORDER:
                w.writerow([s, 'PJ'] + [f'{v:.1f}' for v in data[s]])
            w.writerow(['TOTAL', 'PJ'] + [f'{v:.1f}' for v in totals])
        pending.append((tmp, path))
        quantum = QUANTUM_PT * scale
        print(f'staged {path}   (quantum = +/-{quantum:.1f} PJ)')

        if name in PROSE_CHECKS:
            year, stated, quote = PROSE_CHECKS[name]
            got = totals[YEARS.index(year)]
            ok = abs(got - stated) <= max(2 * quantum, 20.0)
            failures += 0 if ok else 1
            print(f'  {"PASS" if ok else "FAIL"} {year} total: extracted {got:.0f} PJ '
                  f'vs {stated:.0f} PJ stated on p.22 — {quote}')
        if name == 'oil_BAU':
            print(f'  Power (oil to generation), 2020: {data["Power"][0]:.0f} PJ')

    if failures:
        for tmp, _ in pending:
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise SystemExit(f'{failures} prose check(s) FAILED — no CSV written')

    for tmp, path in pending:
        os.replace(tmp, path)
        print(f'wrote {path}')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else '.')
