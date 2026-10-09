#!/usr/bin/env python3
"""Extract the ETP 2.0 industry energy charts (PDF pages 27-29) as numeric series.

Companion to `extract_etp_charts.py` (power), `extract_etp_demand.py` (oil/gas) and
`extract_etp_cooking.py` (cooking); it reuses their `parse_page`. Added 2026-10-09 to check
whether the ETP gives a Nigerian basis for an electric-versus-fuel efficiency ratio in industry
(`../scenario_compass_africa_r10/partial_adjustment/SECTOR_CONVERSION.md`, section 3).

  PDF p.27  total energy demand for chemical production, PJ: gas, hydrogen
  PDF p.28  other industry, high-temperature applications, PJ: oil, gas, biomass,
            biomass CCS, hydrogen
  PDF p.29  other industry, low-temperature applications, PJ: oil, gas, biomass, heat pump

(Pages 25-26, cement and steel, are production in Mtpa, not energy, and are not extracted.)
All three sit in the ETP's net-zero pathway; only 2020 is a starting position.

SERIES are identified by legend colour (swatches paired with the label to their right).
YEARS: on these pages each bar's LEFT edge sits about 3.5 pt right of its year label's left
edge, with 47.3 pt between columns, so every bar is matched to the label whose left edge is
within 6 pt; the script refuses to run if any bar is not.

Validation (GATE): each chart's 2020-2060 growth rate against the rate the ETP prints on the
chart ("+4%", "+3%", "+2%"), within 1 point, since the printed figures are rounded.

Usage:  python3 extract_etp_industry.py <path-to-Nigeria-ETIP-u.pdf> [outdir]
Requires: pypdf, and extract_etp_charts.py alongside this file.
"""
import csv, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_etp_charts import parse_page                      # noqa: E402
from pypdf import PdfReader                                    # noqa: E402

YEARS = [2020, 2025, 2030, 2035, 2040, 2045, 2050, 2055, 2060]
SERIES = {'oil': 'Oil', 'gas': 'Gas', 'biomass': 'Biomass', 'biomass ccs': 'Biomass CCS',
          'hydrogen': 'Hydrogen', 'heat pump': 'Heat pump'}
# page: (chart name, growth rate printed on the chart, %/yr)
CHARTS = {27: ('chemicals', 4.0), 28: ('high_temperature', 3.0), 29: ('low_temperature', 2.0)}


def legend_map(rects, texts):
    sw = [(c, x, y, w, h) for c, x, y, w, h in rects if 18 < w < 21 and 6 < h < 20]
    out = {}
    for c, x, y, w, h in sw:
        cands = [(tx - (x + w), t) for t, tx, ty in texts
                 if x + w - 1 < tx < x + w + 15 and abs(ty - y) < 8 and t.strip().lower() in SERIES]
        if cands:
            out[tuple(round(v, 3) for v in c)] = SERIES[min(cands)[1].strip().lower()]
    return out


def extract(reader, page):
    rects, texts = parse_page(reader.pages[page - 1])
    cmap = legend_map(rects, texts)
    labels = sorted([(int(t.strip()), x) for t, x, y in texts
                     if t.strip().isdigit() and int(t.strip()) in YEARS], key=lambda a: a[1])
    if [l[0] for l in labels] != YEARS:
        raise SystemExit(f'p.{page}: year labels not found in order: {labels}')
    ticks = sorted([(float(t.strip()), y) for t, x, y in texts
                    if x < labels[0][1] - 5 and t.strip().isdigit() and not t.strip().startswith('20')],
                   key=lambda a: a[1])
    (v0, zero_y), (v1, y1) = ticks[0], ticks[-1]
    per_pt = (v1 - v0) / (y1 - zero_y)
    data = {y: {} for y in YEARS}
    for c, x, y, w, h in rects:
        if not (25.5 < w < 27.5 and h > 0 and y >= zero_y - 0.5):
            continue
        key = tuple(round(v, 3) for v in c)
        if key not in cmap:
            raise SystemExit(f'p.{page}: bar colour {key} not in legend map {cmap}')
        d = sorted((abs(x - lx), yr) for yr, lx in labels)
        if d[0][0] > 6:
            raise SystemExit(f'p.{page}: bar at x={x:.1f} matches no year label')
        data[d[0][1]][cmap[key]] = data[d[0][1]].get(cmap[key], 0.0) + h * per_pt
    return data, 0.375 * per_pt


def main():
    pdf = sys.argv[1] if len(sys.argv) > 1 else 'Nigeria-ETIP-u.pdf'
    outdir = sys.argv[2] if len(sys.argv) > 2 else '.'
    reader = PdfReader(pdf)
    charts = {p: extract(reader, p) for p in CHARTS}
    failures = 0
    print('validation against the growth rates printed on the charts:')
    for p, (name, stated) in CHARTS.items():
        data, q = charts[p]
        t0, t1 = sum(data[2020].values()), sum(data[2060].values())
        got = 100 * ((t1 / t0) ** (1 / 40) - 1)
        ok = abs(got - stated) <= 1.0
        failures += not ok
        print(f'  {"PASS" if ok else "FAIL"} p.{p} {name:17} 2020-2060 {got:5.2f}%/yr  printed +{stated:.0f}%'
              f'   (bar quantum +-{q:.2f} PJ)')
    if failures:
        raise SystemExit(f'\n{failures} gating check(s) FAILED -- no CSV written')
    path = os.path.join(outdir, 'etp_industry_PJ.csv')
    tmp = path + '.tmp'
    with open(tmp, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['chart', 'pdf_page', 'series', 'unit'] + [str(y) for y in YEARS])
        for p, (name, _) in CHARTS.items():
            data = charts[p][0]
            for s in sorted({k for y in YEARS for k in data[y]}):
                w.writerow([name, p, s, 'PJ'] + [f'{data[y].get(s, 0.0):.1f}' for y in YEARS])
            w.writerow([name, p, 'TOTAL', 'PJ'] + [f'{sum(data[y].values()):.1f}' for y in YEARS])
    os.replace(tmp, path)
    print(f'\nwrote {path}')


if __name__ == '__main__':
    main()
