#!/usr/bin/env python3
"""Does Nigeria's carbon intensity match Africa's (and IMAGE's Africa R10)?

EXPERIMENT BRANCH `experiment/partial-adjustment`, written 2026-10-09, for
Per's question: the energy systems differ, but perhaps the carbon intensity
matches. If it did, an R10 carbon-intensity path could be a candidate for
transfer (the baseline currently transfers none; see build_nigeria_baseline.py
docstring). Companion: MEMO.md in this directory.

Observed data (2000-2024):
  * CO2 by source, population, GDP: Our World in Data CO2 dataset (Global
    Carbon Budget 2025; GDP Maddison Project 2023, 2011 int-$), African rows
    in ../../owid_co2_africa/
  * Commercial primary energy for Africa and South Africa: the same file
    (Energy Institute / EIA; excludes traditional biomass)
  * Nigeria final energy: IEA, ../../iea_nigeria_2023/
  * Africa final energy: IEA Africa chart exports, ../../iea_africa_2023/
    (copied from MSc-thesis on 2026-10-09; --iea-africa DIR overrides)
Model data: IMAGE 3.2 Africa R10, ../image32_ssp2021/ (2010-2020 rows are
shared calibration values, not observations).

Run: python carbon_intensity_check.py [--iea-africa DIR]
Nigeria's final-energy series are the IEA older release throughout (the only
2000-2023 series held); the current release covers 2023 alone.
"""
import csv, io, json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', '..')
OWID = os.path.join(DATA, 'owid_co2_africa', 'owid_co2_africa_2000_2024.csv')
IEA_NGA = os.path.join(DATA, 'iea_nigeria_2023')
WDI_GROWTH = os.path.join(DATA, 'worldbank_nigeria_gdp', 'NY.GDP.MKTP.KD.ZG.json')
SC = os.path.join(HERE, '..', 'image32_ssp2021')
IEA_AFR = os.path.join(DATA, 'iea_africa_2023')

YEARS = list(range(2000, 2025))
KWH_PER_GJ = 1 / 3.6e-3        # 1 GJ = 277.8 kWh
COAL_EF = 94.6                 # kg CO2/GJ, IPCC 2006 Vol. 2 Table 1.4, other bituminous coal
# Nigeria biomass final energy is not held as a time series; it is estimated
# as domestic biofuels-and-waste production x the 2023 final/supply ratio
# (IEA 2023: 1,233,622 TJ final / 1,372,877 TJ supply), i.e. the charcoal
# conversion share is held at its 2023 value.
NGA_BIO_FINAL_PER_SUPPLY = 1233622.0 / 1372877.0


# --------------------------------------------------------------------------
def load_owid():
    rows = list(csv.DictReader(io.open(OWID, encoding='utf-8')))
    f = lambda v: float(v) if v not in ('', None) else None
    by = {}
    for r in rows:
        key = 'AFRICA_AGG' if r['country'] == 'Africa' else r['iso_code']
        by.setdefault(key, {})[int(r['year'])] = {k: f(r[k]) for k in r if k not in ('country', 'iso_code', 'year')}
    return by


def region(by, exclude=(), need_gdp=False):
    """Sum African countries (iso rows), optionally excluding some and, for
    GDP ratios, restricting to countries with GDP in every year 2000-2022 so
    numerator and denominator cover the same set."""
    isos = [k for k in by if k != 'AFRICA_AGG' and k not in exclude]
    if need_gdp:
        isos = [k for k in isos if all(by[k].get(y, {}).get('gdp') for y in range(2000, 2023))]
    out = {}
    for y in YEARS:
        d = {}
        for c in ('co2', 'coal_co2', 'oil_co2', 'gas_co2', 'flaring_co2', 'cement_co2', 'gdp', 'population'):
            vals = [by[k][y][c] for k in isos if y in by[k] and by[k][y].get(c) is not None]
            d[c] = sum(vals) if vals else None
        out[y] = d
    return out, isos


def combustion(d):
    """Fuel-combustion CO2: total minus flaring and cement (other industry is
    not reported for these countries)."""
    if d['co2'] is None:
        return None
    return d['co2'] - (d['flaring_co2'] or 0) - (d['cement_co2'] or 0)


def iea_series(path, label_filter=None):
    out = {}
    with io.open(path, encoding='utf-8-sig') as fh:
        rows = list(csv.reader(fh))
    for r in rows[1:]:
        if len(r) < 3 or not r[1].strip():
            continue
        if label_filter and r[0] not in label_filter:
            continue
        out[int(r[2])] = out.get(int(r[2]), 0.0) + float(r[1])
    return out


def nigeria_final():
    tfc = iea_series(os.path.join(IEA_NGA, 'total_final_consumption_by_sector_2000_2023.csv'))
    bio = iea_series(os.path.join(IEA_NGA, 'domestic_energy_production_2000_2023.csv'),
                     {'Biofuels and waste'})
    com = {y: tfc[y] - NGA_BIO_FINAL_PER_SUPPLY * bio[y] for y in tfc}
    return tfc, com


def africa_final(d):
    tfc = iea_series(os.path.join(d, 'total_final_consumption_by_sector_africa_2000_2023.csv'))
    bio = {}
    for s in ('residential', 'commercial', 'industry', 'transport'):
        part = iea_series(os.path.join(d, '%s_final_consumption_by_source_africa_2000_2023.csv' % s),
                          {'Biofuels and waste'})
        for y, v in part.items():
            bio[y] = bio.get(y, 0.0) + v
    com = {y: tfc[y] - bio.get(y, 0.0) for y in tfc}
    return tfc, com


def wdi_gdp_index(level_2005):
    rows = json.load(io.open(WDI_GROWTH, encoding='utf-8'))[1]
    g = {int(r['date']): r['value'] for r in rows if r['value'] is not None}
    out = {2005: level_2005}
    for y in range(2006, 2025):
        out[y] = out[y - 1] * (1 + g[y] / 100)
    return out


# --------------------------------------------------------------------------
def pct(a, b):
    return 100 * (b / a - 1) if a and b else float('nan')


def corr(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sxy / (sx * sy) if sx and sy else float('nan')


def trend(s, y0, y1):
    """OLS slope of ln(s) on year, %/yr, over the years present in [y0, y1]."""
    ys = [y for y in range(y0, y1 + 1) if s.get(y)]
    if len(ys) < 4:
        return float('nan')
    lx = [math.log(s[y]) for y in ys]
    mx, my = sum(ys) / len(ys), sum(lx) / len(lx)
    b = sum((y - mx) * (v - my) for y, v in zip(ys, lx)) / sum((y - mx) ** 2 for y in ys)
    return 100 * (math.exp(b) - 1)


def dlog(s, y0, y1):
    return [math.log(s[y] / s[y - 1]) for y in range(y0 + 1, y1 + 1)]


def show(title, unit, series, years=(2000, 2005, 2009, 2010, 2015, 2020, 2022, 2023), ref=None):
    """Levels, plus OLS trends within the two data regimes either side of the
    2010 break in Nigeria's oil CO2 (Global Carbon Budget: 27 -> 59 Mt)."""
    print('  %s (%s)' % (title, unit))
    print('    %-30s' % '' + ''.join('%7d' % y for y in years) + '%10s %10s' % ('tr 00-09', 'tr 10-22'))
    for name, s in series:
        cells = ''.join('%7s' % ('%.3g' % s[y] if s.get(y) else '-') for y in years)
        print('    %-30s%s%9.1f%% %9.1f%%' % (name, cells, trend(s, 2000, 2009), trend(s, 2010, 2022)))
    if ref:
        a, b = ref
        print('    Nigeria / %s, level: %s' % (b[0], ', '.join(
            '%d %.2f' % (y, a[1][y] / b[1][y]) for y in years if a[1].get(y) and b[1].get(y))))


def comove(name_a, a, name_b, b, y0, y1):
    ya = [y for y in range(y0, y1 + 1) if a.get(y) and b.get(y)]
    y0, y1 = ya[0], ya[-1]
    da, db = dlog(a, y0, y1), dlog(b, y0, y1)
    print('    %-24s vs %-26s %d-%d: r(annual change) %+.2f; trend %+.1f%%/yr vs %+.1f%%/yr'
          % (name_a, name_b, y0, y1, corr(da, db), trend(a, y0, y1), trend(b, y0, y1)))


# --------------------------------------------------------------------------
def image_series(fn):
    out = {}
    with io.open(os.path.join(SC, fn), encoding='utf-8-sig') as fh:
        for r in csv.DictReader(fh):
            out.setdefault(r['Scenario name'], {})[int(r['year'])] = float(r['value'])
    return out


SCEN = [('ssp119', 'SSP2021-SSP1-SPA1-19-Default'), ('ssp126', 'SSP2021-SSP1-SPA1-26-Default'),
        ('ssp245', 'SSP2021-SSP2-SPA2-45-Default'), ('ssp370', 'SSP2021-SSP3-Baseline'),
        ('ssp585', 'SSP2021-SSP5-Baseline')]


def main():
    iea_africa = IEA_AFR if os.path.isdir(IEA_AFR) else None
    if '--iea-africa' in sys.argv:
        iea_africa = sys.argv[sys.argv.index('--iea-africa') + 1]
    by = load_owid()
    nga = by['NGA']
    afr, afr_isos = region(by)
    afr_g, afr_g_isos = region(by, need_gdp=True)
    exz_g, _ = region(by, exclude=('ZAF',), need_gdp=True)
    exz, _ = region(by, exclude=('ZAF',))
    rest_g, _ = region(by, exclude=('ZAF', 'NGA'), need_gdp=True)
    rest, _ = region(by, exclude=('ZAF', 'NGA'))
    afr_xn, _ = region(by, exclude=('NGA',))
    print('Check: sum of %d African country rows vs OWID "Africa" CO2, 2023: %.1f vs %.1f Mt'
          % (len(afr_isos), afr[2023]['co2'], by['AFRICA_AGG'][2023]['co2']))
    print('GDP ratios use the %d countries with Maddison GDP in every year 2000-2022 '
          '(missing: %s)' % (len(afr_g_isos), ', '.join(sorted(set(afr_isos) - set(afr_g_isos)))))
    print()

    # A. composition
    print('A. WHAT THE CO2 IS MADE OF (share of fossil-and-industry CO2)')
    print('    %-26s %6s %6s %6s %6s %7s %6s %8s' % ('', 'year', 'coal', 'oil', 'gas', 'flaring', 'cement', 'total Mt'))
    for name, s in (('Nigeria', nga), ('Africa', afr), ('Africa excl. South Africa', exz)):
        for y in (2000, 2010, 2023):
            d = s[y]
            sh = [100 * (d[c] or 0) / d['co2'] for c in ('coal_co2', 'oil_co2', 'gas_co2', 'flaring_co2', 'cement_co2')]
            print('    %-26s %6d %5.0f%% %5.0f%% %5.0f%% %6.0f%% %5.0f%% %8.1f' % (name, y, *sh, d['co2']))
    print()

    # B. intensities
    print('B. CARBON INTENSITIES, OBSERVED')
    g_nga = {y: nga[y]['gdp'] for y in YEARS if nga.get(y, {}).get('gdp')}
    g_nga_wdi = wdi_gdp_index(g_nga[2005])
    co2 = lambda s: {y: s[y]['co2'] for y in YEARS if s.get(y, {}).get('co2')}
    comb = lambda s: {y: combustion(s[y]) for y in YEARS if s.get(y, {}).get('co2')}
    per = lambda num, den, k=1.0: {y: k * num[y] / den[y] for y in num if den.get(y)}
    gdp = lambda s: {y: s[y]['gdp'] for y in YEARS if s.get(y, {}).get('gdp')}
    ci_gdp = {'Nigeria (Maddison GDP)': per(co2(nga), g_nga, 1e9),
              'Nigeria (WDI real growth)': per(co2(nga), g_nga_wdi, 1e9),
              'Africa': per(co2(afr_g), gdp(afr_g), 1e9),
              'Africa excl. South Africa': per(co2(exz_g), gdp(exz_g), 1e9),
              'Africa excl. ZA and NGA': per(co2(rest_g), gdp(rest_g), 1e9)}
    show('B1. CO2 per GDP, fossil and industry', 'kg per 2011 int-$', list(ci_gdp.items()),
         ref=(('Nigeria', ci_gdp['Nigeria (Maddison GDP)']), ('Africa', ci_gdp['Africa'])))
    cb_gdp = {'Nigeria (Maddison GDP)': per(comb(nga), g_nga, 1e9),
              'Africa': per(comb(afr_g), gdp(afr_g), 1e9),
              'Africa excl. South Africa': per(comb(exz_g), gdp(exz_g), 1e9),
              'Africa excl. ZA and NGA': per(comb(rest_g), gdp(rest_g), 1e9)}
    show('B2. CO2 per GDP, fuel combustion only (no flaring, no cement)', 'kg per 2011 int-$',
         list(cb_gdp.items()),
         ref=(('Nigeria', cb_gdp['Nigeria (Maddison GDP)']), ('Africa excl. ZA and NGA', cb_gdp['Africa excl. ZA and NGA'])))

    pe = lambda iso: {y: by[iso][y]['primary_energy_consumption'] for y in YEARS
                      if by[iso].get(y, {}).get('primary_energy_consumption')}
    pe_afr = {y: by['AFRICA_AGG'][y]['primary_energy_consumption'] for y in YEARS
              if by['AFRICA_AGG'].get(y, {}).get('primary_energy_consumption')}
    pe_exz = {y: pe_afr[y] - pe('ZAF')[y] for y in pe_afr if y in pe('ZAF')}
    pe_rest = {y: pe_exz[y] - pe('NGA')[y] for y in pe_exz if y in pe('NGA')}
    tfc_n, com_n = nigeria_final()
    ci_e = {'Nigeria, per commercial final': per(comb(nga), com_n, 1e9 / 1e3),
            'Nigeria, per OWID primary': per(comb(nga), pe('NGA'), 1e9 / (1e9 / KWH_PER_GJ)),
            'Africa, per OWID primary': per(comb(afr), pe_afr, 1e9 / (1e9 / KWH_PER_GJ)),
            'Africa excl. SA, OWID prim.': per(comb(exz), pe_exz, 1e9 / (1e9 / KWH_PER_GJ)),
            'Afr. excl. ZA+NGA, OWID prim.': per(comb(rest), pe_rest, 1e9 / (1e9 / KWH_PER_GJ))}
    print()
    show('B3. Combustion CO2 per unit of commercial energy (no traditional biomass)', 'kg/GJ',
         list(ci_e.items()))
    print('    (Nigeria\'s OWID primary energy is EIA data and erratic -- e.g. 2010 below 2008;')
    print('     its commercial final energy is IEA TFC minus estimated biomass. Final and')
    print('     primary are different denominators: compare changes, not levels, across them.)')
    ci_f = {'Nigeria, per total final': per(co2(nga), tfc_n, 1e9 / 1e3),
            'Nigeria, comb. per total final': per(comb(nga), tfc_n, 1e9 / 1e3)}
    if iea_africa:
        tfc_a, com_a = africa_final(iea_africa)
        ci_f['Africa, per total final'] = per(co2(afr), tfc_a, 1e9 / 1e3)
        ci_f['Africa, comb. per total final'] = per(comb(afr), tfc_a, 1e9 / 1e3)
        tfc_xn = {y: tfc_a[y] - tfc_n[y] for y in tfc_a if y in tfc_n}
        com_xn = {y: com_a[y] - com_n[y] for y in com_a if y in com_n}
        ci_f['Africa excl. NGA, per total final'] = per(co2(afr_xn), tfc_xn, 1e9 / 1e3)
        ci_e2 = {'Nigeria, comb. per comm. final': ci_e['Nigeria, per commercial final'],
                 'Africa, comb. per comm. final': per(comb(afr), com_a, 1e9 / 1e3),
                 'Africa excl. NGA, comb/comm.fin': per(comb(afr_xn), com_xn, 1e9 / 1e3)}
    print()
    show('B4. CO2 per total final energy (biomass in the denominator)', 'kg/GJ', list(ci_f.items()))
    if iea_africa:
        print()
        show('B5. Combustion CO2 per commercial final energy, like for like', 'kg/GJ', list(ci_e2.items()),
             ref=(('Nigeria', ci_e2['Nigeria, comb. per comm. final']), ('Africa excl. NGA', ci_e2['Africa excl. NGA, comb/comm.fin'])))
    else:
        print('    (Africa final energy not found: pass --iea-africa DIR for B4/B5 Africa rows.)')
    print()

    # C. co-movement
    print('C. DO THEY MOVE TOGETHER? Nigeria against the rest of Africa (Nigeria removed, so')
    print('   no mechanical correlation), after the 2010 break; r = correlation of annual log changes')
    for a0, a1 in ((2011, 2022),):
        comove('NGA CO2/GDP', ci_gdp['Nigeria (Maddison GDP)'], 'Africa excl. ZA+NGA', ci_gdp['Africa excl. ZA and NGA'], a0, a1)
        comove('NGA comb/GDP', cb_gdp['Nigeria (Maddison GDP)'], 'Africa excl. ZA+NGA', cb_gdp['Africa excl. ZA and NGA'], a0, a1)
        comove('NGA comb/comm.final', ci_e['Nigeria, per commercial final'], 'Afr. excl. ZA+NGA /prim.', ci_e['Afr. excl. ZA+NGA, OWID prim.'], a0, a1 + 1)
        if iea_africa:
            comove('NGA comb/comm.final', ci_e2['Nigeria, comb. per comm. final'], 'Africa excl. NGA /comm.fin', ci_e2['Africa excl. NGA, comb/comm.fin'], a0, a1 + 1)
            comove('NGA CO2/total final', ci_f['Nigeria, per total final'], 'Africa excl. NGA /tot.fin', ci_f['Africa excl. NGA, per total final'], a0, a1 + 1)
    print()

    # D. IMAGE R10 "history" against observed Africa
    print('D. IMAGE R10 2010-2020 ROWS AGAINST OBSERVED AFRICA (relative change)')
    co2_i, afolu = image_series('Emissions - CO2.csv'), image_series('Emissions - CO2 - AFOLU.csv')
    fe_i, gdp_i = image_series('Final Energy.csv'), image_series('GDP - PPP.csv')
    feb_i = image_series('Final Energy - Solids - Biomass.csv')
    sc = SCEN[2][1]
    ff = {y: co2_i[sc][y] - afolu[sc][y] for y in (2010, 2015, 2020)}
    print('    fossil-and-industry CO2, Mt: IMAGE %s; GCB %s' % (
        ', '.join('%d %.0f' % (y, ff[y]) for y in ff), ', '.join('%d %.0f' % (y, afr[y]['co2']) for y in ff)))
    rows = [('CO2', ff, co2(afr)),
            ('CO2/GDP', {y: ff[y] / gdp_i[sc][y] for y in ff}, ci_gdp['Africa']),
            ('CO2/final energy', {y: ff[y] / fe_i[sc][y] for y in ff},
             ci_f.get('Africa, per total final')),
            ('CO2/commercial final', {y: ff[y] / (fe_i[sc][y] - feb_i[sc][y]) for y in ff},
             ci_e2.get('Africa, comb. per comm. final') if iea_africa else None)]
    print('    %-22s %12s %12s %12s %12s' % ('', 'IMAGE 10-15', 'obs 10-15', 'IMAGE 15-20', 'obs 15-20'))
    for name, im, ob in rows:
        o1 = '%11.1f%%' % pct(ob[2010], ob[2015]) if ob else '%12s' % 'n/a'
        o2 = '%11.1f%%' % pct(ob[2015], ob[2020]) if ob else '%12s' % 'n/a'
        print('    %-22s %11.1f%% %s %11.1f%% %s' % (name, pct(im[2010], im[2015]), o1, pct(im[2015], im[2020]), o2))
    print('    (IMAGE rows are identical across markers to <0.15%; SSP2-4.5 shown. Observed')
    print('     rows: GCB CO2, Maddison GDP, IEA Africa final energy. IMAGE CO2/commercial final')
    print('     uses total CO2 and the observed row combustion CO2, since IMAGE does not separate')
    print('     flaring and cement.)')
    print()

    # E. IMAGE forward: what an R10 carbon-intensity path would carry
    print('E. IMAGE R10 FORWARD: WHAT AN R10 CARBON-INTENSITY PATH WOULD CARRY')
    pe_coal = image_series('Primary Energy - Coal.csv')
    print('    fossil-and-industry CO2 per final energy (all, and commercial = without solid')
    print('    biomass), change from 2020; "ex-coal" removes primary coal x %.1f kg/GJ from the' % COAL_EF)
    print('    numerator (no CCS adjustment, so it fails where coal carries CCS or net CO2 nears 0)')
    print('    %-8s %8s %9s %9s %9s %11s %12s %12s' % ('marker', 'CO2/FE20', 'FE ->50', 'FE ->100',
                                                    'comm->50', 'coal sh.20', 'coal sh.50', 'ex-coal comm->50'))
    for pid, s_ in SCEN:
        f = lambda y: co2_i[s_][y] - afolu[s_][y]
        com = lambda y: fe_i[s_][y] - feb_i[s_][y]
        coal = lambda y: pe_coal[s_][y] * COAL_EF            # EJ x kg/GJ = Mt
        ok50 = f(2050) > coal(2050)
        exc = lambda y: (f(y) - coal(y)) / com(y)
        print('    %-8s %8.1f %8.1f%% %8.1f%% %8.1f%% %10.0f%% %11s %12s' % (
            pid, f(2020) / fe_i[s_][2020], pct(f(2020) / fe_i[s_][2020], f(2050) / fe_i[s_][2050]),
            pct(f(2020) / fe_i[s_][2020], f(2100) / fe_i[s_][2100]),
            pct(f(2020) / com(2020), f(2050) / com(2050)), 100 * coal(2020) / f(2020),
            ('%.0f%%' % (100 * coal(2050) / f(2050))) if ok50 else 'n/a',
            ('%.1f%%' % pct(exc(2020), exc(2050))) if ok50 else 'n/a'))
    print('    (kg CO2/GJ final energy, 2020. Observed Africa coal share of CO2, GCB: %.0f%% in 2020.)'
          % (100 * afr[2020]['coal_co2'] / afr[2020]['co2']))

if __name__ == '__main__':
    main()
