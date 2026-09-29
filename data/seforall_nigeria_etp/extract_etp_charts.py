#!/usr/bin/env python3
"""Extract the ETP 2.0 power-sector charts from Nigeria-ETIP-u.pdf as numeric series.

The two charts on printed pages 17 (installed capacity, GW) and 18 (generation, TWh)
are VECTOR graphics: each stacked-bar segment is a filled rectangle in the PDF content
stream. Neither chart is tabulated anywhere in the document, so the values are recovered
from the rectangle geometry and calibrated against the y-axis tick labels.

Validated against figures the ETP states in prose on the same pages -- see README.md.

Usage:  python3 extract_etp_charts.py <path-to-Nigeria-ETIP-u.pdf> [outdir]
Requires: pypdf
"""
import csv, os, re, sys
from pypdf import PdfReader


def tokenize(s):
    """Minimal PDF content-stream tokenizer: numbers, names, strings, arrays, operators."""
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c in ' \t\r\n':
            i += 1; continue
        if c == '(':                                   # literal string
            d, j = 1, i + 1
            while j < n and d:
                if s[j] == '\\': j += 2; continue
                if s[j] == '(': d += 1
                elif s[j] == ')': d -= 1
                j += 1
            out.append(('str', s[i:j])); i = j; continue
        if c == '<' and i + 1 < n and s[i+1] != '<':    # hex string
            j = s.find('>', i); out.append(('str', s[i:j+1])); i = j + 1; continue
        if c == '[':                                   # array (may contain strings)
            d, j = 1, i + 1
            while j < n and d:
                if s[j] == '\\': j += 2; continue
                if s[j] == '(':
                    dd, j = 1, j + 1
                    while j < n and dd:
                        if s[j] == '\\': j += 2; continue
                        if s[j] == '(': dd += 1
                        elif s[j] == ')': dd -= 1
                        j += 1
                    continue
                if s[j] == '[': d += 1
                elif s[j] == ']': d -= 1
                j += 1
            out.append(('arr', s[i:j])); i = j; continue
        if c == '/':
            j = i + 1
            while j < n and s[j] not in ' \t\r\n/[]()<>': j += 1
            out.append(('name', s[i:j])); i = j; continue
        if c in '<>':
            out.append(('op', s[i:i+2])); i += 2; continue
        j = i
        while j < n and s[j] not in ' \t\r\n/[]()<>': j += 1
        t = s[i:j] if j > i else s[i]; i = max(j, i + 1)
        try:
            out.append(('num', float(t)))
        except ValueError:
            out.append(('op', t))
    return out


def parse_page(page):
    """Return (filled_rects, text_runs) in page coordinates.

    filled_rects: (rgb, x, y, w, h) for every `re` closed by a fill operator.
    text_runs:    (text, x, y) using the text-matrix translation.
    """
    tk = tokenize(page.get_contents().get_data().decode('latin-1'))
    ctm, fill, gs = (1, 0, 0, 1, 0, 0), (0, 0, 0), []
    ops, pend, tm = [], [], None
    rects, texts = [], []

    def apply(m, x, y):
        a, b, c, d, e, f = m
        return (a * x + c * y + e, b * x + d * y + f)

    for i, (typ, val) in enumerate(tk):
        if typ == 'num':
            ops.append(val); continue
        if typ != 'op':
            ops = []; continue
        if val == 'q':
            gs.append((ctm, fill))
        elif val == 'Q':
            if gs: ctm, fill = gs.pop()
        elif val == 'cm' and len(ops) >= 6:
            a, b, c, d, e, f = ops[-6:]
            A, B, C, D, E, F = ctm
            ctm = (a*A + b*C, a*B + b*D, c*A + d*C, c*B + d*D, e*A + f*C + E, e*B + f*D + F)
        elif val == 'g' and ops:
            fill = (ops[-1],) * 3
        elif val == 'rg' and len(ops) >= 3:
            fill = tuple(ops[-3:])
        elif val == 'k' and len(ops) >= 4:                 # CMYK -> RGB
            cy, mg, yl, k = ops[-4:]
            fill = ((1-cy)*(1-k), (1-mg)*(1-k), (1-yl)*(1-k))
        elif val in ('sc', 'scn') and len(ops) >= 3:
            fill = tuple(ops[-3:])
        elif val == 're' and len(ops) >= 4:
            pend = ops[-4:]
        elif val in ('f', 'f*', 'B', 'B*') and pend:
            x, y, w, h = pend
            p0, p1 = apply(ctm, x, y), apply(ctm, x + w, y + h)
            rects.append((fill, min(p0[0], p1[0]), min(p0[1], p1[1]),
                          abs(p1[0] - p0[0]), abs(p1[1] - p0[1])))
            pend = []
        elif val in ('n', 'W', 'W*', 'S'):
            pend = []                                       # clip/stroke, not a fill
        elif val == 'Tm' and len(ops) >= 6:
            tm = tuple(ops[-6:])
        elif val in ('Tj', 'TJ') and tm is not None:
            raw = tk[i-1][1] if i else ''
            txt = ''.join(re.findall(r'\(((?:[^()\\]|\\.)*)\)', raw))
            txt = txt.replace('\\(', '(').replace('\\)', ')')
            if txt.strip():
                p = apply(ctm, tm[4], tm[5])
                texts.append((txt, p[0], p[1]))
        ops = []
    return rects, texts


# Stacking order within each bar == legend reading order. Needed because the
# GENERATION chart assigns ONE colour to TWO series (Solar PV decentralized and
# Onshore wind), so colour alone is ambiguous; position in the stack resolves it.
ORDER = ['Coal', 'Oil', 'Gas On-grid', 'Gas Captive', 'Gas Embedded', 'Biomass',
         'Large Hydro', 'Solar PV', 'Solar PV decentralized', 'Offshore wind',
         'Onshore wind', 'Small hydro', 'Diesel decentralized', 'Hydrogen',
         'Nuclear', 'CCS (Coal, Gas, Biomass)', 'Imports', 'Exports']
YEARS = [2020, 2025, 2030, 2035, 2040, 2045, 2050, 2055, 2060]

CHARTS = {
    # page (1-based), bar baseline y, (y of "0" label, y of top label), value at top label,
    # x of each year column
    'generation_TWh': dict(page=18, base=94.5, ticks=(91.9, 395.9), span=600.0,
                           xs=[60.0, 120.0, 180.75, 240.75, 300.75, 360.75, 420.75, 480.75, 541.5]),
    'capacity_GW':    dict(page=17, base=108.25, ticks=(105.7, 407.7), span=300.0,
                           xs=[53.25, 113.25, 173.25, 233.25, 293.25, 353.25, 413.25, 473.25, 534.0]),
}


def extract(reader, cfg):
    rects, texts = parse_page(reader.pages[cfg['page'] - 1])
    lo, hi = cfg['ticks']
    per_pt = cfg['span'] / (hi - lo)

    # Legend: 6pt swatches paired with the nearest label to their right.
    swatches = [(c, x, y) for c, x, y, w, h in rects
                if 5.5 < w < 7.0 and 5.5 < h < 6.5 and y < 95]
    labels = [(t.strip(), x, y) for t, x, y in texts
              if y < 95 and x < 560 and t.strip() != 'Overall assumptions'
              and not re.fullmatch(r'20\d\d', t.strip())]
    colour_of = {}
    for t, lx, ly in labels:
        c, _, _ = min(swatches, key=lambda s: abs(s[2] - ly) * 3 + abs(s[1] - (lx - 9)))
        colour_of[t] = tuple(round(v, 3) for v in c)

    bars = [r for r in rects if 23 < r[3] < 26]
    data = {}
    for year, x0 in zip(YEARS, cfg['xs']):
        column = sorted([b for b in bars if abs(b[1] - x0) < 2], key=lambda b: b[2])
        ptr, row = 0, {}
        for c, x, y, w, h in column:
            key = tuple(round(v, 3) for v in c)
            while ptr < len(ORDER) and colour_of.get(ORDER[ptr]) != key:
                ptr += 1
            if ptr >= len(ORDER):
                break
            row[ORDER[ptr]] = row.get(ORDER[ptr], 0.0) + h * per_pt
            ptr += 1
        data[year] = row
    return data, h_quantum(per_pt)


def h_quantum(per_pt):
    return 0.75 * per_pt          # the geometry is quantised to 0.75pt


def write_csv(path, data, unit):
    series = [k for k in ORDER if any(k in data[y] for y in YEARS)]
    with open(path, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['series', 'unit'] + [str(y) for y in YEARS])
        for s in series:
            w.writerow([s, unit] + [f'{data[y].get(s, 0.0):.2f}' for y in YEARS])
        w.writerow(['TOTAL', unit] + [f'{sum(data[y].values()):.2f}' for y in YEARS])


def main():
    pdf = sys.argv[1] if len(sys.argv) > 1 else 'Nigeria-ETIP-u.pdf'
    outdir = sys.argv[2] if len(sys.argv) > 2 else '.'
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
    gen, _ = extracted['generation_TWh']
    cap, q_cap = extracted['capacity_GW']
    _, q_gen = extracted['generation_TWh']
    checks = [
        ('gen 2060 solar PV incl. decentralized', gen[2060].get('Solar PV', 0) + gen[2060].get('Solar PV decentralized', 0), 446, q_gen),
        ('gen 2060 hydropower',                   gen[2060].get('Large Hydro', 0) + gen[2060].get('Small hydro', 0), 39, q_gen),
        ('gen 2060 biomass',                      gen[2060].get('Biomass', 0), 32, q_gen),
        ('gen 2060 hydrogen',                     gen[2060].get('Hydrogen', 0), 4, q_gen),
        ('cap 2060 gas (on-grid+captive+embedded)', sum(cap[2060].get(k, 0) for k in ('Gas On-grid', 'Gas Captive', 'Gas Embedded')), 11.8, q_cap),
        ('cap 2060 hydrogen',                     cap[2060].get('Hydrogen', 0), 36, q_cap),
        ('cap 2060 biomass',                      cap[2060].get('Biomass', 0), 6, q_cap),
        ('cap 2060 total excl. imports/exports',  sum(v for k, v in cap[2060].items() if k not in ('Imports', 'Exports')), 277, q_cap),
    ]
    print('validation against ETP prose:')
    failures = 0
    for label, got, stated, q in checks:
        tol = max(2 * q, 1.0)
        ok = abs(got - stated) <= tol
        failures += 0 if ok else 1
        print(f'  {"PASS" if ok else "FAIL"} {label:42} extracted {got:8.1f}   stated {stated:7}   '
              f'diff {got - stated:+6.1f}   tol +/-{tol:.1f}')

    if failures:
        raise SystemExit(f'\n{failures} prose check(s) FAILED — no CSV written')

    print()
    for name, cfg in CHARTS.items():
        data, q = extracted[name]
        unit = name.split('_')[-1]
        path = f'{outdir}/etp_{name}.csv'
        tmp = path + '.tmp'
        write_csv(tmp, data, unit)
        os.replace(tmp, path)
        print(f'wrote {path}  (quantum +/-{q:.2f} {unit})')


if __name__ == '__main__':
    main()
