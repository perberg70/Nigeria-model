#!/usr/bin/env python3
"""Which conversion factors does the partial-adjustment variant need?

EXPERIMENT BRANCH `experiment/partial-adjustment`, written 2026-10-09.
Companion to partial_adjustment_variant.py (imported, not modified) and
CONVERSION_FACTORS.md. The variant takes Burke & Csereklyei (2016) Table 5
coefficients, estimated on

  * 10-year average annual log growth rates, decade-start levels (Eq. 5);
  * income: Penn World Table 7.1 "PPP-converted GDP per capita (chain
    series) at 2005 constant prices" (Appendix A1), demeaned over the
    463-observation sample for the ETA interaction (Table 5 notes);
  * energy: total PRIMARY energy supply (TPES), kgoe per capita
    (Appendix A1, A3),

and applies them to an annual grid, IIASA/OECD ENV-Growth 2025 GDP|PPP in
USD_2015/yr, IMAGE R10 GDP|PPP in USD_2010/yr, and IEA total FINAL
consumption in TJ. This script sorts every unit difference into one of
three bins and quantifies the ones that matter:

  A. time scale    decade coefficients -> annual closing speed LAMBDA
  B. income level  the ETA interaction is the only term that reads the
                   LEVEL of income, so only it needs a level conversion
  C. boundary      TPES coefficients applied to final energy
  D. cancels       pure unit factors (TJ vs kgoe, USD_2010 vs USD_2015)
                   that drop out of log differences and the alpha
                   calibration; verified numerically below

Run: python conversion_factors.py  (output in conversion_factors_output.txt)

Two inputs come from outside this repository and are flagged where used:
Nigeria's PWT 7.1 rgdpch values (FRED series RGDPCHNGA625NUPN, read via
web search on 2026-10-09, not downloaded), and the 463-observation sample
mean of t-10 log GDP per capita, which the paper does not report and which
could not be reconstructed here (PWT 7.1 download blocked by this session's
network policy).
"""
import csv, io, math, os

import partial_adjustment_variant as pav
from partial_adjustment_variant import (
    BASE_YEAR, END_YEAR, MARKERS, NGA_TFE_TJ, BETA_MEAN, ETA, THETA, KAPPA,
    NGA_2023_DEVIATION, interp, series, nigeria_series, pa_path)

HERE = os.path.dirname(os.path.abspath(__file__))
IEA  = os.path.join(HERE, '..', '..', 'iea_nigeria_2023')

# --------------------------------------------------------------------------
# Burke & Csereklyei (2016), CAMA WP 45/2016, Table 5 (p. 19), all columns.
# beta = mean 10-year elasticity, eta = interaction with demeaned t-10 log
# GDP per capita, theta/kappa = t-10 log income / log energy, b25/b75 =
# elasticity at the 25th/75th percentile, lr = reported long-run elasticity.
TABLE5 = {
    'residences':  dict(beta=0.05, eta=0.05,  theta=0.008, kappa=-0.033, b25=0.00, b75=0.11, lr=0.25),
    'agriculture': dict(beta=0.52, eta=0.25,  theta=0.006, kappa=-0.025, b25=0.28, b75=0.78, lr=0.25),
    'transport':   dict(beta=0.66, eta=0.05,  theta=0.029, kappa=-0.035, b25=0.62, b75=0.71, lr=0.84),
    'industry':    dict(beta=0.73, eta=0.25,  theta=0.012, kappa=-0.025, b25=0.50, b75=0.98, lr=0.48),
    'services':    dict(beta=0.56, eta=0.41,  theta=0.033, kappa=-0.040, b25=0.19, b75=0.98, lr=0.83),
    'other':       dict(beta=0.59, eta=-0.04, theta=0.032, kappa=-0.028, b25=0.63, b75=0.55, lr=1.15),
    'total':       dict(beta=0.48, eta=0.13,  theta=0.016, kappa=-0.023, b25=0.36, b75=0.62, lr=0.71),
}
FIVE = ('residences', 'agriculture', 'transport', 'industry', 'services')

# IEA sector names -> paper sectors (Appendix A1). Non-energy use and
# "other non-specified" are not among the paper's five final sectors; the
# paper books them in "Other".
IEA_SECTOR = {
    'Residential': 'residences', 'Agriculture and forestry': 'agriculture',
    'Transport': 'transport', 'Industry': 'industry',
    'Commercial and public services': 'services',
}

# Penn World Table 7.1, Nigeria, rgdpch (2005 I$ per person), as republished
# by FRED (RGDPCHNGA625NUPN). Read via web search 2026-10-09; NOT downloaded
# and not independently verified. Note the year-to-year volatility.
PWT71_NGA = {2006: 1649.33976, 2007: 1912.57771, 2008: 1930.60455,
             2009: 1684.59140, 2010: 1695.45250}

# Table 2 col. 7 (2010 cross-section levels, log income NOT demeaned):
# elasticity = B1 + 2*B2*lnY, 0.63 at the 25th percentile (p. 14).
T2_B1, T2_B2, T2_E25 = -1.20, 0.11, 0.63

KGOE_MJ = 41.868        # IEA: 1 toe = 41.868 GJ

IIASA = os.path.join(HERE, '..', '..', 'iiasa_ssp_nigeria',
                     'Population_GDP_PPP_IIASA_SSP_15_Nigeria.csv')


def iea_csv(name):
    out = {}
    with io.open(os.path.join(IEA, name), encoding='utf-8-sig') as fh:
        rows = list(csv.reader(fh))
    for r in rows[1:]:
        if len(r) >= 2 and r[1].strip():
            out[r[0]] = float(r[1])
    return out


def iiasa_historical(variable, unit):
    with io.open(IIASA, encoding='utf-8-sig') as fh:
        for r in csv.DictReader(fh):
            if (r['scenario'] == 'Historical Reference' and r['variable'] == variable
                    and r['unit'] == unit):
                return {int(k): float(v) for k, v in r.items()
                        if k.strip().isdigit() and v not in ('', None)}


# --------------------------------------------------------------------------
# Scenario runner: the variant's plain/recalibrated/delta-off leg with every
# parameter exposed, so each conversion can be switched on by itself.
def run_markers(nga, reg=None, gdp_unit='billion USD_2015/yr', anchor_tj=NGA_TFE_TJ):
    """nga/reg: dicts with beta_mean, eta, b_target, lam, g_dev0. Returns
    {pid: (var/cur 2050, var/cur 2100, var 2100 TJ)}; 'cur' is the current
    construction, unchanged (0.36 L + 0.065 L^2, old-law R). reg may also be
    a function of the marker id, for region parameters that vary by marker."""
    reg = reg or nga
    reg_for = reg if callable(reg) else (lambda pid: reg)
    fe, r10_gdp, r10_pop = (series('Final Energy.csv'), series('GDP - PPP.csv'),
                            series('Population.csv'))
    pop = nigeria_series('Population', 'million', 1e6)
    gdp = nigeria_series('GDP|PPP', gdp_unit, 1e9)
    years = list(range(BASE_YEAR, END_YEAR + 1))
    out = {}
    for pid, (scen, narrative) in MARKERS.items():
        p0 = pop[narrative][BASE_YEAR]
        log_g = {y: math.log(interp(y, gdp[narrative]) / interp(y, pop[narrative]))
                 for y in years}
        r_log_g = {y: math.log(interp(y, r10_gdp[scen]) / interp(y, r10_pop[scen]))
                   for y in years}
        log_x0 = math.log(anchor_tj / pop[narrative][BASE_YEAR])
        r_log_x0 = math.log(interp(BASE_YEAR, fe[scen]) / interp(BASE_YEAR, r10_pop[scen]))
        n = pa_path(years, log_g, log_x0, beta_mean=nga['beta_mean'], eta=nga['eta'],
                    b_target=nga['b_target'], lam=nga['lam'], g_dev0=nga['g_dev0'])
        rp = reg_for(pid)
        r = pa_path(years, r_log_g, r_log_x0, beta_mean=rp['beta_mean'], eta=rp['eta'],
                    b_target=rp['b_target'], lam=rp['lam'], g_dev0=rp['g_dev0'])
        res = {}
        for y in (2050, END_YEAR):
            pt = interp(y, pop[narrative])
            fe_ratio = interp(y, fe[scen]) / interp(BASE_YEAR, fe[scen])
            pop_ratio = interp(y, r10_pop[scen]) / interp(BASE_YEAR, r10_pop[scen])
            Lr = r_log_g[y] - r_log_g[BASE_YEAR]
            L = log_g[y] - log_g[BASE_YEAR]
            r_var = fe_ratio / (pop_ratio * math.exp(r[y] - r[BASE_YEAR]))
            r_old = fe_ratio / (pop_ratio * math.exp(0.36 * Lr + 0.065 * Lr * Lr))
            var = anchor_tj * (pt / p0) * math.exp(n[y] - n[BASE_YEAR]) * r_var
            cur = anchor_tj * (pt / p0) * math.exp(0.36 * L + 0.065 * L * L) * r_old
            res[y] = (var, cur)
        out[pid] = (res[2050][0] / res[2050][1], res[END_YEAR][0] / res[END_YEAR][1],
                    res[END_YEAR][0])
    return out


def base_params(**kw):
    p = dict(beta_mean=BETA_MEAN, eta=ETA, b_target=-THETA / KAPPA, lam=-KAPPA,
             g_dev0=NGA_2023_DEVIATION)
    p.update(kw)
    return p


def print_runs(label_runs):
    print('  %-34s' % 'leg' + ''.join('%14s' % pid for pid in MARKERS))
    print('  %-34s' % '' + ''.join('%14s' % 'v/c50  v/c100' for _ in MARKERS))
    for label, runs in label_runs:
        print('  %-34s' % label + ''.join(
            '%7.3f%7.3f' % (runs[pid][0], runs[pid][1]) for pid in MARKERS))
    print()


# --------------------------------------------------------------------------
# A. TIME SCALE
def decade_recursion(log_g, g0):
    dec = {BASE_YEAR: 0.0}
    for y in range(BASE_YEAR + 10, END_YEAR + 1, 10):
        dg = log_g[y] - log_g[y - 10]
        beta = BETA_MEAN + ETA * (NGA_2023_DEVIATION + (log_g[y - 10] - g0))
        dec[y] = (1 + 10 * KAPPA) * dec[y - 10] + beta * dg + 10 * THETA * (log_g[y - 10] - g0)
    return dec


def section_a():
    rho10 = 1 + 10 * KAPPA                    # decade retention of a level gap
    lams = [('linear  -kappa', -KAPPA),
            ('geometric 1-(1+10k)^0.1', 1 - rho10 ** 0.1),
            ('log  -ln(1+10k)/10', -math.log(rho10) / 10)]
    print('A. TIME SCALE: decade coefficients -> annual closing speed')
    print('  Eq. 5 is in annual-average growth units on decade-start levels, so a')
    print('  level gap is retained 1+10*kappa = %.3f per decade. Candidate annual' % rho10)
    print('  closing speeds (theta scales with lambda; b = -theta/kappa = %.4f fixed):'
          % (-THETA / KAPPA))
    for name, lam in lams:
        print('    %-26s lambda = %.5f  decade retention %.4f  annual theta %.5f  half-life %.1f yr'
              % (name, lam, (1 - lam) ** 10, lam * -THETA / KAPPA, math.log(2) / -math.log(1 - lam)))
    print('  beta, eta and the decade dummies need no time conversion: beta and eta')
    print('  are growth-on-growth ratios and the dummies are already in annual-')
    print('  growth units (Table 5 notes: "differenced logs divided by 10").')
    print()

    years = list(range(BASE_YEAR, END_YEAR + 1))
    g0 = math.log(8000.0)
    shock = {y: g0 + (math.log(1.10) if y >= 2024 else 0.0) for y in years}
    growth = {y: g0 + 0.02 * (y - BASE_YEAR) for y in years}
    d1, d2 = decade_recursion(shock, g0), decade_recursion(growth, g0)
    print('  Test 1 (shock) and Test 2 (2%/yr growth): annual PA minus decade recursion')
    print('  %-26s %10s %10s %10s | %10s %10s %10s' %
          ('lambda', 'T1 2033', 'T1 2063', 'T1 max|.|', 'T2 23-33', 'T2 63-73', 'T2 max|.|'))
    for name, lam in lams:
        p1 = pa_path(years, shock, 0.0, lam=lam, g_dev0=NGA_2023_DEVIATION)
        p2 = pa_path(years, growth, 0.0, lam=lam, g_dev0=NGA_2023_DEVIATION)
        g1 = {y: p1[y] - d1[y] for y in d1 if y > BASE_YEAR}
        w = {y: (p2[y + 10] - p2[y] - (d2[y + 10] - d2[y])) / 0.2
             for y in range(BASE_YEAR, END_YEAR - 10, 10)}
        print('  %-26s %10.4f %10.4f %10.4f | %10.4f %10.4f %10.4f' %
              (name, g1[2033], g1[2063], max(abs(v) for v in g1.values()),
               w[2023], w[2063], max(abs(v) for v in w.values())))
    print('  (T1 in log points of energy; T2 in window-elasticity units)')
    print()
    print('  Scenario runs (plain target, eta active, R recalibrated):')
    print_runs([(name, run_markers(base_params(lam=lam))) for name, lam in lams])


# --------------------------------------------------------------------------
# B. INCOME LEVEL
def section_b():
    print('B. INCOME LEVEL: only the ETA interaction reads the level of income')
    print('  beta*dg and the target slope use log DIFFERENCES (any constant price-base')
    print('  factor cancels) and alpha absorbs the level, so the income conversion')
    print('  only enters through d = ln Y_NGA - mean_463(ln Y_t-10) in PWT 7.1 units.')
    pop = iiasa_historical('Population', 'million')
    pc = {}
    for unit in ('billion USD_2010/yr', 'billion USD_2015/yr', 'billion USD_2017/yr'):
        g = iiasa_historical('GDP|PPP', unit)
        pc[unit] = {y: g[y] / pop[y] * 1e3 for y in (2010, 2020, 2025)}
        pc[unit][2023] = interp(2023, {y: g[y] for y in (2020, 2025)}) / \
            interp(2023, {y: pop[y] for y in (2020, 2025)}) * 1e3
    growth_10_23 = pc['billion USD_2015/yr'][2023] / pc['billion USD_2015/yr'][2010]
    print('  Nigeria GDP per head, OECD ENV-Growth 2025 (IIASA export), PPP:')
    for unit, v in pc.items():
        print('    %-22s 2010 %7.0f   2023 %7.0f' % (unit.replace('billion ', ''), v[2010], v[2023]))
    print('    real growth per head 2010->2023: x%.4f (%.2f log points); identical in all three'
          % (growth_10_23, math.log(growth_10_23) * 100))
    print('    rows: the three price bases differ by a constant factor')
    print('  Nigeria, PWT 7.1 rgdpch (2005 I$), FRED RGDPCHNGA625NUPN [via web search, unverified]:')
    print('    ' + '  '.join('%d %.0f' % kv for kv in sorted(PWT71_NGA.items())))
    pwt10 = PWT71_NGA[2010]
    pwt23 = pwt10 * growth_10_23
    lo, hi = min(PWT71_NGA.values()) * growth_10_23, max(PWT71_NGA.values()) * growth_10_23
    print('    spliced 2023 = PWT 7.1 2010 x OECD growth since 2010 = %.0f (2006-2010 base range %.0f-%.0f)'
          % (pwt23, lo, hi))
    gap = math.log(pc['billion USD_2010/yr'][2010] / pwt10)
    print('    level gap in 2010, OECD USD_2010 PPP vs PWT 7.1: %.2f log units (x%.2f) --' % (gap, math.exp(gap)))
    print('    before any 2010->2005 deflation; a price-base conversion factor cannot close it')
    print()
    e = lambda b1, b2, e25: math.exp((e25 - b1) / (2 * b2))
    p25_2010 = e(T2_B1, T2_B2, T2_E25)
    rng = sorted(e(b1, b2, e25) for b1 in (T2_B1 - .005, T2_B1 + .005)
                 for b2 in (T2_B2 - .005, T2_B2 + .005) for e25 in (T2_E25 - .005, T2_E25 + .005))
    print('  The sample mean of ln Y_t-10 is not reported. Table 5 fixes the 25th percentile')
    print('  at mean - %.3f. Only reference point for its level: Table 2 col. 7 (2010' % -NGA_2023_DEVIATION)
    print('  cross-section, undemeaned): 25th percentile = exp((0.63+1.20)/0.22) = $%.0f' % p25_2010)
    print('  (coefficient rounding alone spans $%.0f-$%.0f). The pooled t-10 sample' % (rng[0], rng[-1]))
    print('  (start years 1960-2000) sits lower, by an unmeasured amount.')
    print('  d for Nigeria 2023 (spliced PWT 7.1 value $%.0f) as a function of the unknown' % pwt23)
    print('  25th percentile of the t-10 sample, and the starting 10-year elasticity:')
    print('  %-30s %8s %8s' % ('assumed 25th pct (2005 I$)', 'd', 'beta_0'))
    cases = [('= Nigeria (current assumption)', pwt23)] + \
        [('$%d' % p, p) for p in (2000, 2500, 3000, 3500)] + \
        [('$%.0f (Table 2, 2010)' % p25_2010, p25_2010)]
    ds = []
    for label, p25 in cases:
        d = NGA_2023_DEVIATION - math.log(p25 / pwt23)
        ds.append((label, d))
        print('  %-30s %8.3f %8.3f' % (label, d, BETA_MEAN + ETA * d))
    print()
    print('  Scenario runs, Nigeria AND region at the same d (as in the variant):')
    print_runs([('d %.2f  (%s)' % (d, label[:18]), run_markers(base_params(g_dev0=d)))
                for label, d in ds])

    # Region: own position, from IMAGE R10 USD_2010 PPP against the IIASA
    # USD_2010 row (different vintages of the same price base).
    r_gdp, r_pop = series('GDP - PPP.csv'), series('Population.csv')
    nga_10 = pc['billion USD_2010/yr'][2023]
    print('  Region at its own position: d_R = d + ln(R10 GDP per head / Nigeria), 2023,')
    print('  both in USD_2010 PPP (IMAGE SSP2021 vs OECD ENV-Growth 2025, different vintages):')
    rows = []
    for pid, (scen, _) in MARKERS.items():
        r10 = interp(2023, r_gdp[scen]) / interp(2023, r_pop[scen]) * 1e3
        off = math.log(r10 / nga_10)
        print('    %-7s R10 %6.0f  Nigeria %6.0f  ln ratio %+.3f' % (pid, r10, nga_10, off))
        rows.append(off)
    off = sum(rows) / len(rows)
    print_runs([('same d (variant)', run_markers(base_params())),
                ('region d_R = d %+.3f' % off,
                 run_markers(base_params(), reg=base_params(g_dev0=NGA_2023_DEVIATION + off)))])


# --------------------------------------------------------------------------
# C. BOUNDARY: TPES coefficients on final energy
def section_c():
    tes = iea_csv('total_energy_supply_2023.csv')
    tfc = iea_csv('total_final_consumption_by_sector_2023.csv')
    tes_total, tfc_total = sum(tes.values()), sum(tfc.values())
    sec = {IEA_SECTOR[k]: v for k, v in tfc.items() if k in IEA_SECTOR}
    five = sum(sec.values())
    other = tes_total - five
    print('C. BOUNDARY: Table 5 "total" is TPES; the variant drives IEA total final consumption')
    print('  Nigeria 2023 (IEA): TES %.0f TJ, TFC %.0f TJ, TES/TFC %.3f; five paper sectors'
          % (tes_total, tfc_total, tes_total / tfc_total))
    print('  %.0f TJ (%.1f%% of TFC; non-energy use and non-specified are "Other" in the paper)'
          % (five, 100 * five / tfc_total))
    pop23 = interp(2023, iiasa_historical('Population', 'million')) * 1e6
    print('  per head: TES %.0f kgoe, TFC %.0f kgoe (1 kgoe = %.3f MJ); paper 2010 cross-section'
          % (tes_total * 1e6 / KGOE_MJ / pop23, tfc_total * 1e6 / KGOE_MJ / pop23, KGOE_MJ))
    print('  means: all 2,725.8, low-income 396.2 kgoe TPES (Appendix A3)')
    w_tes = {s: v / tes_total for s, v in sec.items()}
    w_tes['other'] = other / tes_total
    w_fin = {s: v / five for s, v in sec.items()}
    keys = ('beta', 'b25', 'b75', 'eta', 'kappa', 'lr')
    agg = lambda w, k: sum(w[s] * TABLE5[s][k] for s in w)
    so = w_tes['other']
    top = {k: (TABLE5['total'][k] - so * TABLE5['other'][k]) / (1 - so) for k in keys}
    print('  weights, share of TES:   ' + '  '.join('%s %.3f' % (s[:5], w) for s, w in w_tes.items()))
    print('  weights, share of five:  ' + '  '.join('%s %.3f' % (s[:5], w) for s, w in w_fin.items()))
    print()
    print('  %-44s' % '' + ''.join('%8s' % k for k in keys))
    print('  %-44s' % 'Table 5 total (published)' + ''.join('%8.3f' % TABLE5['total'][k] for k in keys))
    print('  %-44s' % 'Eq. 3 check: six sectors weighted by TES' + ''.join('%8.3f' % agg(w_tes, k) for k in keys))
    print('  %-44s' % 'final, bottom-up: five sectors by TFC share' + ''.join('%8.3f' % agg(w_fin, k) for k in keys))
    print('  %-44s' % 'final, top-down: (total - s_O*other)/(1-s_O)' + ''.join('%8.3f' % top[k] for k in keys))
    print('  (lr is the share-weighted reported long-run elasticity; kappa the share-weighted')
    print('   convergence coefficient. Shares are 2023 values held fixed, Eq. 3 is exact only')
    print('   for small changes; a sector-by-sector PA would let them drift.)')
    print()
    bu = dict(beta_mean=agg(w_fin, 'beta'), eta=agg(w_fin, 'eta'), b_target=agg(w_fin, 'lr'),
              lam=-agg(w_fin, 'kappa'), g_dev0=NGA_2023_DEVIATION)
    td = dict(beta_mean=top['beta'], eta=top['eta'], b_target=top['lr'], lam=-top['kappa'],
              g_dev0=NGA_2023_DEVIATION)
    # The two routes agree on the elasticity at Nigeria's percentile and,
    # roughly, on the long run; they disagree on eta and kappa, which Eq. 3
    # does not decompose (the TES-weighted check misses both). This leg
    # converts only the agreed terms and leaves eta and kappa at Table 5.
    b25_f = (agg(w_fin, 'b25') + top['b25']) / 2
    lr_f = (agg(w_fin, 'lr') + top['lr']) / 2
    agreed = base_params(beta_mean=b25_f - ETA * NGA_2023_DEVIATION, b_target=lr_f)
    print('  agreed-terms leg: beta_0 %.3f (mean of the two routes), b_target %.3f; eta %.2f'
          % (b25_f, lr_f, ETA))
    print('  and lambda %.3f unconverted' % -KAPPA)

    # Region at its own IMAGE 2023 sector mix. IMAGE reports Residential and
    # Commercial together; it is split in Nigeria's residences:services ratio
    # (an assumption), and the unallocated remainder is left out.
    rc_res = w_fin['residences'] / (w_fin['residences'] + w_fin['services'])
    reg_w = {}
    for pid, (scen, _) in MARKERS.items():
        f = {k: interp(2023, series('Final Energy - %s.csv' % k)[scen])
             for k in ('Industry', 'Residential and Commercial', 'Transportation')}
        tot = sum(f.values())
        w = {'industry': f['Industry'] / tot, 'transport': f['Transportation'] / tot,
             'residences': rc_res * f['Residential and Commercial'] / tot,
             'services': (1 - rc_res) * f['Residential and Commercial'] / tot}
        reg_w[pid] = dict(beta_mean=agg(w, 'beta'), eta=agg(w, 'eta'), b_target=agg(w, 'lr'),
                          lam=-agg(w, 'kappa'), g_dev0=NGA_2023_DEVIATION)
    w245 = reg_w['ssp245']
    print('  region bottom-up at its own 2023 mix (SSP2-4.5): beta %.3f, b25 %.3f, eta %.3f,'
          % (w245['beta_mean'], w245['beta_mean'] + w245['eta'] * NGA_2023_DEVIATION, w245['eta']))
    print('  kappa %.3f, lr %.3f' % (-w245['lam'], w245['b_target']))
    print()
    print('  Scenario runs (R recalibrated through whichever law the region is given):')
    print_runs([('TPES total (variant)', run_markers(base_params())),
                ('final bottom-up, both', run_markers(bu)),
                ('final bottom-up, region own mix', run_markers(bu, reg=lambda pid: reg_w[pid])),
                ('final top-down, both', run_markers(td)),
                ('final agreed terms, both', run_markers(agreed)),
                ('final bottom-up, Nigeria only', run_markers(bu, reg=base_params()))])
    print('  The last leg breaks closure: IMAGE "Final Energy" has the same boundary as')
    print('  Nigeria\'s TFC, so the region must be stripped with the same final-energy law.')
    print()


# --------------------------------------------------------------------------
# D. FACTORS THAT CANCEL
def section_d():
    print('D. PURE UNIT FACTORS CANCEL (numerical check)')
    ref = run_markers(base_params())
    alt_gdp = run_markers(base_params(), gdp_unit='billion USD_2010/yr')
    alt_e = run_markers(base_params(), anchor_tj=NGA_TFE_TJ * 1e6 / KGOE_MJ)
    d_gdp = max(abs(alt_gdp[p][1] - ref[p][1]) for p in ref)
    d_e = max(abs(alt_e[p][1] - ref[p][1]) for p in ref)
    print('  GDP in USD_2010 instead of USD_2015 rows:   max |change| in var/cur 2100 = %.1e' % d_gdp)
    print('  energy anchor in kgoe instead of TJ:          max |change| in var/cur 2100 = %.1e' % d_e)
    print('  IMAGE R10 GDP stays in USD_2010: it enters only as log changes and in R.')
    print()


if __name__ == '__main__':
    section_a()
    section_b()
    section_c()
    section_d()
