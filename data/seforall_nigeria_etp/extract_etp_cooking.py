#!/usr/bin/env python3
"""Extract the ETP 2.0 cooking charts (PDF pages 37-40) as numeric series.

Companion to `extract_etp_charts.py` (power, pp.17-18) and `extract_etp_demand.py`
(oil/gas demand, p.22). The four cooking charts are vector stacked-bar graphics with
no underlying table anywhere in the document:

  PDF p.37  national cooking demand, '000 stove units, by fuel
  PDF p.38  urban cooking demand,    '000 stove units, by fuel
  PDF p.39  rural cooking demand,    '000 stove units, by fuel
  PDF p.40  total cooking fuel demand, PJ, by fuel

All four sit in the ETP's "Transition towards Net Zero 2060" section, so from 2025 on they
are the ETP's NET-ZERO POLICY PATHWAY, not a baseline. Only 2020 is a starting position.

SERIES ARE IDENTIFIED BY LEGEND COLOUR, not by stack position (several series are zero in
several years). Every page carries filled-rectangle legend swatches (~20x15 pt, drawn BELOW
the plot's zero line), and the colour map is re-derived from each page's own legend on every
run. The swatches have bar-like widths, so bars are taken only from ABOVE the zero line --
an earlier draft of this file counted swatches as bars, which put phantom 'traditional
biomass' in 2040 and phantom 'LPG' in 2055.

YEAR COLUMNS are assigned to the nearest printed year label. The script refuses to run if any
bar is not clearly nearer one label than the next (guard against the half-spacing ambiguity
that made the p.22 NZE charts unextractable).

Validation: every figure the ETP states in prose about these charts is checked. Checks marked
GATE must pass within tolerance or no CSV is written. Checks marked INFO are loose prose
("3-fold", "90%") that the extraction does not reproduce exactly; they are printed, and the
mismatch is recorded in README.md rather than hidden.

Usage:  python3 extract_etp_cooking.py <path-to-Nigeria-ETIP-u.pdf> [outdir]
Requires: pypdf, and extract_etp_charts.py alongside this file.
"""
import csv, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_etp_charts import parse_page                      # noqa: E402
from pypdf import PdfReader                                    # noqa: E402

YEARS = [2020, 2025, 2030, 2035, 2040, 2045, 2050, 2055, 2060]
SERIES = {'lpg': 'LPG', 'electric': 'Electric', 'electricity': 'Electric',
          'biofuels': 'Biofuels', 'traditional biomass': 'Traditional biomass',
          'biomass': 'Biomass'}

# page (1-based): chart name, unit, legend-source page (None = own legend)
CHARTS = {
    37: ('national_stoves', "'000 units", None),
    38: ('urban_stoves',    "'000 units", None),
    39: ('rural_stoves',    "'000 units", None),
    40: ('fuel_demand',     'PJ',         None),
}


def legend_map(rects, texts):
    """Colour -> series name, from ~20x15pt swatches paired with the label to their right."""
    sw = [(c, x, y, w, h) for c, x, y, w, h in rects if 18 < w < 21 and 13 < h < 16]
    out = {}
    for c, x, y, w, h in sw:
        cands = [(tx - (x + w), t) for t, tx, ty in texts
                 if tx > x + w - 1 and abs(ty - y) < 6 and t.strip().lower() in SERIES]
        if cands:
            out[tuple(round(v, 3) for v in c)] = SERIES[min(cands)[1].strip().lower()]
    return out


def axis_scale(texts):
    """(value per pt, y of the '0' label) from the y-axis tick labels left of the plot."""
    ticks = []
    for t, x, y in texts:
        s = t.strip().replace(',', '')
        if x < 70 and s.isdigit() and not (len(s) == 4 and s.startswith('20') and y < 70):
            ticks.append((float(s), y))
    ticks.sort(key=lambda a: a[1])
    (v0, y0), (v1, y1) = ticks[0], ticks[-1]
    return (v1 - v0) / (y1 - y0), y0


def extract(reader, page):
    name, unit, legend_page = CHARTS[page]
    rects, texts = parse_page(reader.pages[page - 1])
    lrects, ltexts = (rects, texts) if legend_page is None else parse_page(reader.pages[legend_page - 1])
    cmap = legend_map(lrects, ltexts)
    if len(cmap) < 3:
        raise SystemExit(f'p.{page}: legend map has {len(cmap)} entries -- refusing')
    per_pt, zero_y = axis_scale(texts)
    labels = sorted([(int(t.strip()), x) for t, x, y in texts
                     if t.strip().isdigit() and len(t.strip()) == 4 and int(t.strip()) in YEARS and y < 100 and x < 560],
                    key=lambda a: a[1])
    if [l[0] for l in labels] != YEARS:
        raise SystemExit(f'p.{page}: year labels not found in order: {labels}')
    spacing = (labels[-1][1] - labels[0][1]) / (len(labels) - 1)
    bars = [(c, x, y, w, h) for c, x, y, w, h in rects if 20 < w < 31 and x < 560 and h > 0 and y > zero_y]
    data = {y: {} for y in YEARS}
    for c, x, y, w, h in bars:
        key = tuple(round(v, 3) for v in c)
        if key not in cmap:
            raise SystemExit(f'p.{page}: bar colour {key} not in legend map {cmap}')
        d = sorted((abs(x - lx), yr) for yr, lx in labels)
        if d[1][0] - d[0][0] < 0.5 * spacing:
            raise SystemExit(f'p.{page}: bar at x={x:.1f} is ambiguous between {d[0][1]} and {d[1][1]}')
        s = cmap[key]
        data[d[0][1]][s] = data[d[0][1]].get(s, 0.0) + h * per_pt
    return name, unit, data, 0.75 * per_pt


def main():
    pdf = sys.argv[1] if len(sys.argv) > 1 else 'Nigeria-ETIP-u.pdf'
    outdir = sys.argv[2] if len(sys.argv) > 2 else '.'
    reader = PdfReader(pdf)
    charts = {p: extract(reader, p) for p in CHARTS}
    nat, urb, rur, fuel = (charts[p][2] for p in (37, 38, 39, 40))
    qf = charts[40][3]
    share = lambda d, y, s: d[y].get(s, 0) / sum(d[y].values())

    # (label, extracted, stated, tolerance, gate)
    checks = [
        ('p.40 biofuels peak 2060, "36 PJ"',              fuel[2060].get('Biomass', 0), 36, max(2 * qf, 0.05 * 36), True),
        ('p.40 LPG peak mid-2020s, "58 PJ"',               max(fuel[y].get('LPG', 0) for y in (2020, 2025, 2030)), 58, max(2 * qf, 0.1 * 58), True),
        ('p.39 rural e-stoves 2040, ">50%"',               100 * share(rur, 2040, 'Electric'), 50, None, True),
        ('p.39 rural biofuels 2060, "40%"',                100 * share(rur, 2060, 'Biofuels'), 40, 2.0, True),
        # Internal consistency, not prose: the national chart must equal urban + rural.
        ('p.37 national 2020 = p.38 urban + p.39 rural (%)', 100 * sum(nat[2020].values()) / (sum(urb[2020].values()) + sum(rur[2020].values())), 100, 1.0, True),
        ('p.37 national 2060 = p.38 urban + p.39 rural (%)', 100 * sum(nat[2060].values()) / (sum(urb[2060].values()) + sum(rur[2060].values())), 100, 1.0, True),
        ('p.40 total fuel 2020->2060, "decrease by 20%"',  100 * (1 - sum(fuel[2060].values()) / sum(fuel[2020].values())), 20, None, False),
        ('p.38 urban e-stoves 2060, "90%"',                100 * share(urb, 2060, 'Electric'), 90, None, False),
        ('p.37 electric 2030->2060, "grows 3-fold"',       nat[2060].get('Electric', 0) / nat[2030].get('Electric', 1), 3, None, False),
    ]
    failures = 0
    print('validation against ETP prose:')
    for label, got, stated, tol, gate in checks:
        if tol is None:
            ok = got > stated if '>' in label else None
        else:
            ok = abs(got - stated) <= tol
        tag = ('PASS' if ok else 'FAIL') if (gate and ok is not None) else 'INFO'
        if gate and not ok:
            failures += 1
        print(f'  {tag} {label:48} extracted {got:8.2f}  stated {stated}')
    if failures:
        raise SystemExit(f'\n{failures} gating check(s) FAILED -- no CSV written')

    path = os.path.join(outdir, 'etp_cooking.csv')
    tmp = path + '.tmp'
    with open(tmp, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['chart', 'pdf_page', 'series', 'unit'] + [str(y) for y in YEARS])
        for p, (name, unit, data, _) in charts.items():
            for s in sorted({k for y in YEARS for k in data[y]}):
                w.writerow([name, p, s, unit] + [f'{data[y].get(s, 0.0):.1f}' for y in YEARS])
            w.writerow([name, p, 'TOTAL', unit] + [f'{sum(data[y].values()):.1f}' for y in YEARS])
    os.replace(tmp, path)
    print(f'\nwrote {path}')
    e, l = nat[2020].get('Electric', 0), nat[2020].get('LPG', 0)
    print(f'2020 national: electric {e:.0f}k, LPG {l:.0f}k stoves -> electric share of (electric+LPG) = {e / (e + l):.4f}')


if __name__ == '__main__':
    main()
